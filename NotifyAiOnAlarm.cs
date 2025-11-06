/*
BVMS skripta 1 – salje AI-ju da se pojavio alarm

Ovo ubacis u BVMS Configuration Client → Scripts → Client Script i vezes na “On New Alarm” (ili “On Accept”, kako ti je lakse). Ona samo salje ime kamere AI serveru na port 8000.

Promeni IP na IP tvog PC-ja sa Pythonom.
*/


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
        string json = $"{{\"camera\":\"{cam}\"}}";

        using (var wc = new WebClient())
        {
            wc.Headers[HttpRequestHeader.ContentType] = "application/json";
            // IP/port tvog python AI servera
            wc.UploadData("http://192.168.1.200:8000/bvms-event", "POST", Encoding.UTF8.GetBytes(json));
        }
    }
}
