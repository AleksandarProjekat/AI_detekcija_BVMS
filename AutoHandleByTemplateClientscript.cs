// ScriptType: ClientScript
// ScriptLanguage: CS

/*
Ovo ide na “On Accept” (ili “On Alarm Opened”). Ako je 0–9 → clear. Ako je 10+ → pusti TPL_xx i ostavi alarm.
*/
using System;
using Bosch.Vms.Core;
using Bosch.Vms.SDK;

[BvmsScriptClass()]
public class AutoHandleByTemplate
{
    private readonly IClientApi _api;
    public AutoHandleByTemplate(IClientApi api) { _api = api; }

    [Scriptlet("PUT-YOUR-GUID-HERE")]
    public void Run()
    {
        var alarm = _api.AlarmManager.GetCurrentAlarm();
        if (alarm == null) return;

        string textData = alarm.EventData.TextData ?? "";
        int templateId = GetTemplateId(textData);

        // tehnicki / lazni (0-9) -> auto clear
        if (templateId >= 0 && templateId <= 9)
        {
            _api.AlarmManager.ClearAlarm(alarm.Id);
            return;
        }

        // ostalo -> pusti njihov sablon
        string workflow = $"TPL_{templateId:D2}";
        var task = _api.ServerApi.TaskManager.GetTaskByName(workflow);
        if (task != null)
            _api.ServerApi.TaskManager.ExecuteTask(task);

        // NE clearujemo - da operater vidi
    }

    private int GetTemplateId(string textData)
    {
        const string key = "TEMPLATE_ID=";
        int i = textData.IndexOf(key, StringComparison.OrdinalIgnoreCase);
        if (i < 0) return -1;
        int start = i + key.Length;
        int end = textData.IndexOf(";", start);
        if (end < 0) end = textData.Length;
        string idStr = textData.Substring(start, end - start);
        int.TryParse(idStr, out var id);
        return id;
    }
}
