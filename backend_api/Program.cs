using OmniGuard.BackendApi.Configuration;
using OmniGuard.BackendApi.Services;
using Microsoft.Extensions.FileProviders;

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

var snapshotAssetRoot = Path.GetFullPath(Path.Combine(app.Environment.ContentRootPath, "..", "ai_engine", "artifacts"));
Directory.CreateDirectory(snapshotAssetRoot);

app.UseStaticFiles(new StaticFileOptions
{
    FileProvider = new PhysicalFileProvider(snapshotAssetRoot),
    RequestPath = "/assets",
    OnPrepareResponse = context =>
    {
        context.Context.Response.Headers.CacheControl = "no-store, no-cache, must-revalidate";
        context.Context.Response.Headers.Pragma = "no-cache";
        context.Context.Response.Headers.Expires = "0";
    },
});

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
