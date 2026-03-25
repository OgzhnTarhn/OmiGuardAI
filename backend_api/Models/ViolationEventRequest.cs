using System.ComponentModel.DataAnnotations;

namespace OmniGuard.BackendApi.Models;

public sealed class ViolationEventRequest
{
    [Required]
    public string EventType { get; init; } = string.Empty;

    [Required]
    public string CameraId { get; init; } = string.Empty;

    [Required]
    public string SiteId { get; init; } = string.Empty;

    [Range(0, int.MaxValue)]
    public int TrackId { get; init; }

    [Range(0.0, 1.0)]
    public double Confidence { get; init; }

    public DateTimeOffset TimestampUtc { get; init; }

    [Required]
    public string Model { get; init; } = string.Empty;

    [Required]
    public string Device { get; init; } = string.Empty;

    [Range(0, int.MaxValue)]
    public int LineY { get; init; }

    [Range(1, int.MaxValue)]
    public int FrameWidth { get; init; }

    [Range(1, int.MaxValue)]
    public int FrameHeight { get; init; }

    [Required]
    public PointDto Center { get; init; } = new();

    [Required]
    public BoundingBoxDto BoundingBox { get; init; } = new();
}

public sealed class PointDto
{
    [Range(0, int.MaxValue)]
    public int X { get; init; }

    [Range(0, int.MaxValue)]
    public int Y { get; init; }
}

public sealed class BoundingBoxDto
{
    [Range(0, int.MaxValue)]
    public int X1 { get; init; }

    [Range(0, int.MaxValue)]
    public int Y1 { get; init; }

    [Range(0, int.MaxValue)]
    public int X2 { get; init; }

    [Range(0, int.MaxValue)]
    public int Y2 { get; init; }
}
