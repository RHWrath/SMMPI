namespace SMMPI.Domain.Interfaces;

public interface IToolPathService
{
    string ResolveAdbExecutable();

    string ResolveScrcpyExecutable();

    string ResolveScrcpyDirectory();

    void EnsureScrcpyAvailable();
}
