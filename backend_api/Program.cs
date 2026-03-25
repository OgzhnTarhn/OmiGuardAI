using OmniGuard.BackendApi.Configuration;
using OmniGuard.BackendApi.Services;

var builder = WebApplication.CreateBuilder(args);

builder.WebHost.UseUrls(builder.Configuration.GetValue<string>("Server:HttpUrl") ?? "http://localhost:8080");

builder.Logging.ClearProviders();
builder.Logging.AddConsole();
builder.Logging.AddDebug();

builder.Services.Configure<ViolationStoreOptions>(builder.Configuration.GetSection("ViolationStore"));
builder.Services.Configure<TelegramOptions>(builder.Configuration.GetSection("Telegram"));
builder.Services.AddCors(options =>
{
    options.AddPolicy(
        "Dashboard",
        policy => policy.AllowAnyOrigin().AllowAnyHeader().AllowAnyMethod());
});
builder.Services.AddHttpClient();
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSingleton<IViolationNotifier, LoggingViolationNotifier>();
builder.Services.AddSingleton<IViolationNotifier, TelegramViolationNotifier>();
builder.Services.AddSingleton<IViolationEventService, InMemoryViolationEventService>();

var app = builder.Build();

app.UseCors("Dashboard");

app.MapGet(
    "/health",
    () => Results.Ok(new
    {
        status = "ok",
        service = "backend_api",
        timestampUtc = DateTimeOffset.UtcNow,
    }));

app.MapControllers();

app.Run();
