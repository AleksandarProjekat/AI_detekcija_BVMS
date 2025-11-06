var builder = WebApplication.CreateBuilder(args);

builder.Services.AddSingleton<TemplateService>();

// ovde moras da registrujes BVMS IServerApi iz tvog okruzenja
// builder.Services.AddSingleton<IServerApi>(...);

builder.Services.AddControllers();

var app = builder.Build();
app.MapControllers();
app.Run();
