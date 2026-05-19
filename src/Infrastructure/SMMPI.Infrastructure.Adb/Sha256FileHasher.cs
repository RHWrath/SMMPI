using System.Security.Cryptography;

namespace SMMPI.Infrastructure.Adb;

public sealed class Sha256FileHasher
{
    public async Task<string> ComputeAsync(string path, CancellationToken cancellationToken)
    {
        await using var stream = File.OpenRead(path);
        var hash = await SHA256.HashDataAsync(stream, cancellationToken).ConfigureAwait(false);
        return Convert.ToHexString(hash).ToLowerInvariant();
    }
}
