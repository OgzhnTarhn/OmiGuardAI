using System.Net.Http.Json;
using Microsoft.Extensions.Options;
using OmniGuard.BackendApi.Configuration;
using OmniGuard.BackendApi.Models;

namespace OmniGuard.BackendApi.Services;

public sealed class TelegramViolationNotifier(
    IHttpClientFactory httpClientFactory,
    IOptions<TelegramOptions> telegramOptions,
    ILogger<TelegramViolationNotifier> logger) : IViolationNotifier
{
    private readonly IHttpClientFactory _httpClientFactory = httpClientFactory;
    private readonly TelegramOptions _telegramOptions = telegramOptions.Value;
    private readonly ILogger<TelegramViolationNotifier> _logger = logger;

    public async Task NotifyAsync(ViolationRecord record, CancellationToken cancellationToken = default)
    {
        if (!_telegramOptions.Enabled)
        {
            return;
        }

        if (string.IsNullOrWhiteSpace(_telegramOptions.BotToken) || string.IsNullOrWhiteSpace(_telegramOptions.ChatId))
        {
            _logger.LogWarning("Telegram notifier is enabled but BotToken or ChatId is missing.");
            return;
        }

        var requestUri = $"https://api.telegram.org/bot{_telegramOptions.BotToken}/sendMessage";
        var payload = new
        {
            chat_id = _telegramOptions.ChatId,
            text = BuildMessage(record),
        };

        var client = _httpClientFactory.CreateClient();
        var response = await client.PostAsJsonAsync(requestUri, payload, cancellationToken);

        if (!response.IsSuccessStatusCode)
        {
            var responseBody = await response.Content.ReadAsStringAsync(cancellationToken);
            _logger.LogWarning(
                "Telegram notification failed. StatusCode={StatusCode} Body={Body}",
                response.StatusCode,
                responseBody);
        }
    }

    private static string BuildMessage(ViolationRecord record)
    {
        return
            "OmniGuard AI alert\n" +
            $"Event: {record.Event.EventType}\n" +
            $"Site: {record.Event.SiteId}\n" +
            $"Camera: {record.Event.CameraId}\n" +
            $"TrackId: {record.Event.TrackId}\n" +
            $"Confidence: {record.Event.Confidence:F2}\n" +
            $"Model: {record.Event.Model}\n" +
            $"TimeUtc: {record.ReceivedAtUtc:O}";
    }
}
