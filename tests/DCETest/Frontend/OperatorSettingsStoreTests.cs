using SMMPI.App.Services;

namespace Teststraat.Frontend;

[TestClass]
public sealed class OperatorSettingsStoreTests
{
    private string _settingsPath = null!;

    [TestInitialize]
    public void SetUp()
    {
        _settingsPath = Path.Combine(Path.GetTempPath(), $"smmpi-settings-{Guid.NewGuid():N}.json");
    }

    [TestCleanup]
    public void TearDown()
    {
        if (File.Exists(_settingsPath))
        {
            File.Delete(_settingsPath);
        }
    }

    [TestMethod]
    public void Load_WhenFileDoesNotExist_ReturnsEmptySettings()
    {
        var store = new OperatorSettingsStore(_settingsPath);

        var settings = store.Load();

        Assert.IsTrue(string.IsNullOrEmpty(settings.OfficerName));
        Assert.IsTrue(string.IsNullOrEmpty(settings.CaseNumber));
    }

    [TestMethod]
    public void Save_ThenLoad_RoundTripsOperatorFields()
    {
        var store = new OperatorSettingsStore(_settingsPath);
        var expected = new OperatorSettings
        {
            OfficerName = "Agent Jansen",
            CaseNumber = "ZA-2026-001",
            MediaLibraryFolder = @"C:\media",
            CaseLogFolder = @"C:\cases",
        };

        store.Save(expected);
        var actual = store.Load();

        Assert.AreEqual(expected.OfficerName, actual.OfficerName);
        Assert.AreEqual(expected.CaseNumber, actual.CaseNumber);
        Assert.AreEqual(expected.MediaLibraryFolder, actual.MediaLibraryFolder);
        Assert.AreEqual(expected.CaseLogFolder, actual.CaseLogFolder);
    }
}
