using Microsoft.AspNetCore.Mvc;
using OmniGuard.BackendApi.Models;
using OmniGuard.BackendApi.Services;

namespace OmniGuard.BackendApi.Controllers;

[ApiController]
[Route("api/[controller]")]
public sealed class ViolationsController(IViolationEventService violationEventService) : ControllerBase
{
    [HttpPost]
    public async Task<ActionResult<CreateViolationResponse>> Create(
        [FromBody] ViolationEventRequest request,
        CancellationToken cancellationToken)
    {
        if (request.BoundingBox.X2 <= request.BoundingBox.X1 || request.BoundingBox.Y2 <= request.BoundingBox.Y1)
        {
            ModelState.AddModelError(nameof(request.BoundingBox), "BoundingBox coordinates are invalid.");
        }

        if (request.Center.X < 0 || request.Center.X > request.FrameWidth ||
            request.Center.Y < 0 || request.Center.Y > request.FrameHeight)
        {
            ModelState.AddModelError(nameof(request.Center), "Center point must stay within the frame.");
        }

        if (!ModelState.IsValid)
        {
            return ValidationProblem(ModelState);
        }

        var record = await violationEventService.RecordAsync(request, cancellationToken);

        return Accepted(new CreateViolationResponse
        {
            Id = record.Id,
            Status = "accepted",
            ReceivedAtUtc = record.ReceivedAtUtc,
        });
    }

    [HttpGet]
    public ActionResult<IReadOnlyCollection<ViolationRecord>> GetRecent([FromQuery] int limit = 50)
    {
        return Ok(violationEventService.GetRecent(limit));
    }
}
