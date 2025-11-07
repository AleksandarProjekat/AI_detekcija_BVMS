// ScriptType: ClientScript
// ScriptLanguage: CS

using System;
using System.Net;
using System.Text;
using Bosch.Vms.Core;
using Bosch.Vms.SDK;

[BvmsScriptClass()]
public class NotifyAiOnAlarm
{
    private readonly IClientApi _api;

    public NotifyAiOnAlarm(IClientApi api)
    {
        _api = api;
    }

    // stavi ovde svoj GUID iz BVMS-a
    [Scriptlet("PUT-YOUR-GUID-HERE")]
    public void Run()
    {
        // 1) Probaj prvo "noviji" nacin – CurrentAlarm
        IAlarm alarm = null;

        try
        {
            // neke verzije imaju CurrentAlarm
            alarm = _api.AlarmManager.CurrentAlarm;
        }
        catch
        {
            // ako nema CurrentAlarm, padamo na listu
        }

        // 2) Ako nema current, uzmi prvi iz liste
        if (alarm == null)
        {
            var alarms = _api.AlarmManager.Alarms;
            if (alarms == null || alarms.Count == 0)
            {
                // nema alarma, nema slanja
                return;
            }

            alarm = alarms[0];
        }

        // 3) Izvuci ime izvora iz eventa (npr. CAM_WH_01)
        var srcName = alarm.EventData != null ? alarm.EventData.SourceName : null;
        if (string.IsNullOrEmpty(srcName))
        {
            // ako nemamo ime, nema svrhe slati
            return;
        }

        // 4) Sastavi JSON
        // ovako izbegavamo problem sa { } i $
        string json = string.Format("{{\"camera\":\"{0}\",\"duration\":10}}", srcName);

        // 5) Pošalji na tvoj Python endpoint
        try
        {
            using (var wc = new WebClient())
            {
                wc.Headers[HttpRequestHeader.ContentType] = "application/json";
                // OVDE STAVI SVOJ URL (ngrok ili lokalni python)
                wc.UploadData("http://192.168.1.200:8000/bvms-event", "POST", Encoding.UTF8.GetBytes(json));
            }
        }
        catch (Exception ex)
        {
            // u BVMS skriptu obicno nema potrebe za throw,
            // ali mozes logovati u trace ako imas
            System.Diagnostics.Debug.WriteLine("NotifyAiOnAlarm error: " + ex.Message);
        }
    }
}
