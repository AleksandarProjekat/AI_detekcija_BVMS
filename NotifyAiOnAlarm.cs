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
    public NotifyAiOnAlarm(IClientApi api) { _api = api; }

    [Scriptlet("PUT-YOUR-GUID-HERE")]
    public void Run()
    {
        var alarm = _api.AlarmManager.GetCurrentAlarm();
        if (alarm == null) return;

        string cam = alarm.EventData.SourceName;  // npr. CAM_WH_01
        // sada saljemo i duration da python zna koliko da snima
        string json = $"{{\"camera\":\"{cam}\",\"duration\":10}}";

        using (var wc = new WebClient())
        {
            wc.Headers[HttpRequestHeader.ContentType] = "application/json";
            wc.UploadData("http://192.168.1.200:8000/bvms-event", "POST", Encoding.UTF8.GetBytes(json));
        }
    }
}
