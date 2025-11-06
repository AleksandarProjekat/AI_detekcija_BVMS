// AiTemplateEvent.cs
//Ovo je ASP.NET Core API. On dobije {template_id: 2, camera: "CAM_WH_01", ...} i napravi user event u BVMS-u gde je Description = "AI_TRIGGER=1;TEMPLATE_ID=2;...".
using System;

public class AiTemplateEvent
{
    public int TemplateId { get; set; }
    public string Camera { get; set; }
    public double Confidence { get; set; }
    public DateTime Timestamp { get; set; }
}
