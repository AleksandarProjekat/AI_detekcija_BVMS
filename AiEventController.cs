// AiEventController.cs
using Microsoft.AspNetCore.Mvc;
using System;
// using Bosch.Vms.SDK; // dodaj pravi namespace

[ApiController]
[Route("ai-event")]
public class AiEventController : ControllerBase
{
    private readonly TemplateService _templates;
    private readonly IServerApi _serverApi; // iz BVMS-a

    public AiEventController(TemplateService templates, IServerApi serverApi)
    {
        _templates = templates;
        _serverApi = serverApi;
    }

    [HttpPost]
    public IActionResult Post([FromBody] AiTemplateEvent dto)
    {
        string templateName = _templates.GetName(dto.TemplateId);

        string textData =
            $"AI_TRIGGER=1;TEMPLATE_ID={dto.TemplateId};TEMPLATE_NAME={templateName};CAMERA={dto.Camera};CONF={dto.Confidence};TIME={dto.Timestamp:o}";

        // upisi user event u BVMS (to ce biti Text Data)
        var userEvent = _serverApi.EventManager.CreateUserEvent();
        userEvent.Description = textData;
        _serverApi.EventManager.RaiseUserEvent(userEvent);

        // opciono: ako imas taskove TPL_00 ... TPL_39 u BVMS-u
        string workflow = $"TPL_{dto.TemplateId:D2}";
        var task = _serverApi.TaskManager.GetTaskByName(workflow);
        if (task != null)
            _serverApi.TaskManager.ExecuteTask(task);

        return Ok(new { status = "ok" });
    }
}
