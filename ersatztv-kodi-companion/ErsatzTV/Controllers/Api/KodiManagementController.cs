using System.Security.Cryptography;
using System.Text;
using ErsatzTV.Application.Channels;
using ErsatzTV.Application.Filler;
using ErsatzTV.Application.Playouts;
using ErsatzTV.Application.ProgramSchedules;
using ErsatzTV.Application.Search;
using ErsatzTV.Application.Scheduling;
using ErsatzTV.Application.Watermarks;
using ErsatzTV.Core;
using ErsatzTV.ViewModels;
using MediatR;
using Microsoft.AspNetCore.Mvc;

namespace ErsatzTV.Controllers.Api;

/// <summary>
/// Opt-in management surface for the Kodi add-on. Disabled unless
/// ETV_KODI_MANAGEMENT_KEY is set. The reverse proxy should additionally
/// restrict this route to trusted networks.
/// </summary>
[ApiController]
[Route("api/kodi-management")]
public class KodiManagementController(IMediator mediator, IConfiguration configuration) : ControllerBase
{
    private bool Authorized()
    {
        string expected = configuration["ETV_KODI_MANAGEMENT_KEY"]
            ?? Environment.GetEnvironmentVariable("ETV_KODI_MANAGEMENT_KEY");
        string supplied = Request.Headers["X-ErsatzTV-Kodi-Key"].FirstOrDefault();
        if (string.IsNullOrWhiteSpace(expected) || string.IsNullOrWhiteSpace(supplied)) return false;
        byte[] left = SHA256.HashData(Encoding.UTF8.GetBytes(expected));
        byte[] right = SHA256.HashData(Encoding.UTF8.GetBytes(supplied));
        return CryptographicOperations.FixedTimeEquals(left, right);
    }

    private IActionResult Guard() => string.IsNullOrWhiteSpace(
            configuration["ETV_KODI_MANAGEMENT_KEY"] ?? Environment.GetEnvironmentVariable("ETV_KODI_MANAGEMENT_KEY"))
        ? Problem("Kodi management API is disabled; set ETV_KODI_MANAGEMENT_KEY", statusCode: 503)
        : Unauthorized();

    private IActionResult From<T>(Either<BaseError, T> result) =>
        result.Match<IActionResult>(Ok, error => Problem(error.ToString()));

    [HttpGet("capabilities")]
    public IActionResult Capabilities() => Authorized()
        ? Ok(new
        {
            apiVersion = 1,
            features = new[] { "channels", "schedules", "schedule-items", "playouts", "blocks", "fillers", "watermarks", "content-search", "ffmpeg-profiles", "smart-collections" }
        })
        : Guard();

    [HttpGet("channels")]
    public async Task<IActionResult> Channels(CancellationToken token) => Authorized()
        ? Ok(await mediator.Send(new GetAllChannels(true), token))
        : Guard();

    [HttpGet("channels/{id:int}")]
    public async Task<IActionResult> Channel(int id, CancellationToken token)
    {
        if (!Authorized()) return Guard();
        Option<ChannelViewModel> result = await mediator.Send(new GetChannelById(id), token);
        return result.Match<IActionResult>(value => Ok(value), () => NotFound());
    }

    [HttpPost("channels")]
    public async Task<IActionResult> CreateChannel([FromBody] ChannelEditViewModel model, CancellationToken token) =>
        Authorized() ? From(await mediator.Send(model.ToCreate(), token)) : Guard();

    [HttpPut("channels/{id:int}")]
    public async Task<IActionResult> UpdateChannel(int id, [FromBody] ChannelEditViewModel model, CancellationToken token)
    {
        if (!Authorized()) return Guard();
        model.Id = id;
        return From(await mediator.Send(model.ToUpdate(), token));
    }

    [HttpDelete("channels/{id:int}")]
    public async Task<IActionResult> DeleteChannel(int id, CancellationToken token) => Authorized()
        ? From(await mediator.Send(new DeleteChannel(id), token))
        : Guard();

    [HttpGet("schedules")]
    public async Task<IActionResult> Schedules([FromQuery] string query, CancellationToken token) => Authorized()
        ? Ok(await mediator.Send(new GetPagedProgramSchedules(query, 0, 10000), token))
        : Guard();

    [HttpGet("schedules/{id:int}")]
    public async Task<IActionResult> Schedule(int id, CancellationToken token)
    {
        if (!Authorized()) return Guard();
        Option<ProgramScheduleViewModel> result = await mediator.Send(new GetProgramScheduleById(id), token);
        return result.Match<IActionResult>(value => Ok(value), () => NotFound());
    }

    [HttpPost("schedules")]
    public async Task<IActionResult> CreateSchedule([FromBody] ProgramScheduleEditViewModel model, CancellationToken token) =>
        Authorized() ? From(await mediator.Send(model.ToCreate(), token)) : Guard();

    [HttpPut("schedules/{id:int}")]
    public async Task<IActionResult> UpdateSchedule(int id, [FromBody] ProgramScheduleEditViewModel model, CancellationToken token)
    {
        if (!Authorized()) return Guard();
        model.Id = id;
        return From(await mediator.Send(model.ToUpdate(), token));
    }

    [HttpDelete("schedules/{id:int}")]
    public async Task<IActionResult> DeleteSchedule(int id, CancellationToken token) => Authorized()
        ? From(await mediator.Send(new DeleteProgramSchedule(id), token))
        : Guard();

    [HttpGet("schedules/{id:int}/items")]
    public async Task<IActionResult> ScheduleItems(int id, CancellationToken token) => Authorized()
        ? Ok(await mediator.Send(new GetProgramScheduleItems(id), token))
        : Guard();

    [HttpPut("schedules/{id:int}/items")]
    public async Task<IActionResult> ReplaceScheduleItems(
        int id,
        [FromBody] List<ReplaceProgramScheduleItem> items,
        CancellationToken token) => Authorized()
        ? From(await mediator.Send(new ReplaceProgramScheduleItems(id, items), token))
        : Guard();

    [HttpGet("playouts")]
    public async Task<IActionResult> Playouts([FromQuery] string query, CancellationToken token) => Authorized()
        ? Ok(await mediator.Send(new GetPagedPlayouts(query, 0, 10000), token))
        : Guard();

    [HttpPost("playouts")]
    public async Task<IActionResult> CreatePlayout([FromBody] KodiPlayoutRequest request, CancellationToken token)
    {
        if (!Authorized()) return Guard();
        CreatePlayout command = request.Kind?.ToLowerInvariant() switch
        {
            "block" => new CreateBlockPlayout(request.ChannelId),
            "sequential" => new CreateSequentialPlayout(request.ChannelId, request.ScheduleFile),
            "scripted" => new CreateScriptedPlayout(request.ChannelId, request.ScheduleFile),
            "externaljson" => new CreateExternalJsonPlayout(request.ChannelId, request.ScheduleFile),
            _ => new CreateClassicPlayout(request.ChannelId, request.ProgramScheduleId ?? 0)
        };
        return From(await mediator.Send(command, token));
    }

    [HttpPut("playouts/{id:int}/file")]
    public async Task<IActionResult> UpdatePlayoutFile(int id, [FromBody] KodiPlayoutFileRequest request, CancellationToken token)
    {
        if (!Authorized()) return Guard();
        Either<BaseError, Unit> result = request.Kind?.ToLowerInvariant() switch
        {
            "sequential" => await mediator.Send(new UpdateSequentialPlayout(id, request.ScheduleFile), token),
            "scripted" => await mediator.Send(new UpdateScriptedPlayout(id, request.ScheduleFile), token),
            _ => await mediator.Send(new UpdateExternalJsonPlayout(id, request.ScheduleFile), token)
        };
        return From(result);
    }

    [HttpDelete("playouts/{id:int}")]
    public async Task<IActionResult> DeletePlayout(int id, CancellationToken token) => Authorized()
        ? From(await mediator.Send(new DeletePlayout(id), token))
        : Guard();

    [HttpGet("block-groups")]
    public async Task<IActionResult> BlockGroups(CancellationToken token) => Authorized()
        ? Ok(await mediator.Send(new GetAllBlockGroups(), token))
        : Guard();

    [HttpPost("block-groups")]
    public async Task<IActionResult> CreateBlockGroup([FromBody] KodiNameRequest request, CancellationToken token) =>
        Authorized() ? From(await mediator.Send(new CreateBlockGroup(request.Name), token)) : Guard();

    [HttpDelete("block-groups/{id:int}")]
    public async Task<IActionResult> DeleteBlockGroup(int id, CancellationToken token)
    {
        if (!Authorized()) return Guard();
        Option<BaseError> result = await mediator.Send(new DeleteBlockGroup(id), token);
        return result.Match<IActionResult>(error => Problem(error.ToString()), () => Ok());
    }

    [HttpGet("blocks")]
    public async Task<IActionResult> Blocks(CancellationToken token) => Authorized()
        ? Ok(await mediator.Send(new GetAllBlocks(), token))
        : Guard();

    [HttpGet("blocks/{id:int}")]
    public async Task<IActionResult> Block(int id, CancellationToken token)
    {
        if (!Authorized()) return Guard();
        Option<BlockViewModel> block = await mediator.Send(new GetBlockById(id), token);
        if (block.IsNone) return NotFound();
        return Ok(new { block = block.IfNoneUnsafe(default(BlockViewModel)), items = await mediator.Send(new GetBlockItems(id), token) });
    }

    [HttpPost("blocks")]
    public async Task<IActionResult> CreateBlock([FromBody] KodiBlockCreateRequest request, CancellationToken token) =>
        Authorized() ? From(await mediator.Send(new CreateBlock(request.BlockGroupId, request.Name), token)) : Guard();

    [HttpPut("blocks/{id:int}")]
    public async Task<IActionResult> UpdateBlock(int id, [FromBody] KodiBlockUpdateRequest request, CancellationToken token) =>
        Authorized()
            ? From(await mediator.Send(new ReplaceBlockItems(request.BlockGroupId, id, request.Name, request.Minutes, request.StopScheduling, request.Items), token))
            : Guard();

    [HttpDelete("blocks/{id:int}")]
    public async Task<IActionResult> DeleteBlock(int id, CancellationToken token)
    {
        if (!Authorized()) return Guard();
        Option<BaseError> result = await mediator.Send(new DeleteBlock(id), token);
        return result.Match<IActionResult>(error => Problem(error.ToString()), () => Ok());
    }

    [HttpGet("fillers")]
    public async Task<IActionResult> Fillers(CancellationToken token) => Authorized()
        ? Ok(await mediator.Send(new GetAllFillerPresets(), token))
        : Guard();

    [HttpPost("fillers")]
    public async Task<IActionResult> CreateFiller([FromBody] FillerPresetEditViewModel model, CancellationToken token) =>
        Authorized() ? From(await mediator.Send(model.ToUpdate(), token)) : Guard();

    [HttpPut("fillers/{id:int}")]
    public async Task<IActionResult> UpdateFiller(int id, [FromBody] FillerPresetEditViewModel model, CancellationToken token)
    {
        if (!Authorized()) return Guard();
        model.Id = id;
        return From(await mediator.Send(model.ToEdit(), token));
    }

    [HttpDelete("fillers/{id:int}")]
    public async Task<IActionResult> DeleteFiller(int id, CancellationToken token) => Authorized()
        ? From(await mediator.Send(new DeleteFillerPreset(id), token))
        : Guard();

    [HttpGet("watermarks")]
    public async Task<IActionResult> Watermarks(CancellationToken token) => Authorized()
        ? Ok(await mediator.Send(new GetAllWatermarks(), token))
        : Guard();

    [HttpPost("watermarks")]
    public async Task<IActionResult> CreateWatermark([FromBody] WatermarkEditViewModel model, CancellationToken token) =>
        Authorized() ? From(await mediator.Send(model.ToCreate(), token)) : Guard();

    [HttpPut("watermarks/{id:int}")]
    public async Task<IActionResult> UpdateWatermark(int id, [FromBody] WatermarkEditViewModel model, CancellationToken token)
    {
        if (!Authorized()) return Guard();
        model.Id = id;
        return From(await mediator.Send(model.ToUpdate(), token));
    }

    [HttpDelete("watermarks/{id:int}")]
    public async Task<IActionResult> DeleteWatermark(int id, CancellationToken token) => Authorized()
        ? From(await mediator.Send(new DeleteWatermark(id), token))
        : Guard();

    [HttpGet("search/{kind}")]
    public async Task<IActionResult> Search(string kind, [FromQuery] string query, CancellationToken token)
    {
        if (!Authorized()) return Guard();
        return kind.ToLowerInvariant() switch
        {
            "collections" => Ok(await mediator.Send(new SearchCollections(query), token)),
            "multi-collections" => Ok(await mediator.Send(new SearchMultiCollections(query), token)),
            "smart-collections" => Ok(await mediator.Send(new SearchSmartCollections(query), token)),
            "rerun-collections" => Ok(await mediator.Send(new SearchRerunCollections(query), token)),
            "shows" => Ok(await mediator.Send(new SearchTelevisionShows(query), token)),
            "seasons" => Ok(await mediator.Send(new SearchTelevisionSeasons(query), token)),
            "artists" => Ok(await mediator.Send(new SearchArtists(query), token)),
            _ => BadRequest("Unknown content search kind")
        };
    }
}

public record KodiPlayoutRequest(string Kind, int ChannelId, int? ProgramScheduleId, string ScheduleFile);
public record KodiPlayoutFileRequest(string Kind, string ScheduleFile);
public record KodiNameRequest(string Name);
public record KodiBlockCreateRequest(int BlockGroupId, string Name);
public record KodiBlockUpdateRequest(
    int BlockGroupId,
    string Name,
    int Minutes,
    ErsatzTV.Core.Domain.Scheduling.BlockStopScheduling StopScheduling,
    List<ReplaceBlockItem> Items);
