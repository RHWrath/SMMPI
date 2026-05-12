namespace SMMPI.Domain.Interfaces;

public interface ISessionLogService
{
    Task LogAsync(string message, CancellationToken cancellationToken);
}
