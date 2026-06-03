using SMMPI.Infrastructure.Plugins.Tools;
using System;
using System.Collections.Generic;
using System.Text;

namespace Teststraat
{
    [TestClass]
    public class ProcessHandlerTests
    {
        [TestMethod]
        public async Task TryRunProcessAsync_WithValidCommand_ReturnsTrue()
        {
            var result = await ProcessHandler.TryRunProcessAsync(
                "cmd.exe",
                "/c echo hello",
                Directory.GetCurrentDirectory());

            Assert.IsTrue(result);
        }

        [TestMethod]
        public async Task TryRunProcessAsync_WithInvalidCommand_ReturnsFalse()
        {
            var result = await ProcessHandler.TryRunProcessAsync(
                "this-file-does-not-exist.exe",
                "",
                Directory.GetCurrentDirectory());

            Assert.IsFalse(result);
        }

        [TestMethod]
        public async Task RunProcessCheckedAsync_WithValidCommand_DoesNotThrow()
        {
            await ProcessHandler.RunProcessCheckedAsync(
                "cmd.exe",
                "/c echo hello",
                Directory.GetCurrentDirectory());
        }

        [TestMethod]
        public async Task RunProcessCheckedAsync_WithNonZeroExitCode_ThrowsInvalidOperationException()
        {
            await Assert.ThrowsAsync<InvalidOperationException>(async () =>
            {
                await ProcessHandler.RunProcessCheckedAsync(
                    "cmd.exe",
                    "/c exit 1",
                    Directory.GetCurrentDirectory());
            });
        }

        [TestMethod]
        public async Task RunProcessCheckedAsync_CapturesStandardOutput()
        {
            var lines = new List<string>();

            await ProcessHandler.RunProcessCheckedAsync(
                "cmd.exe",
                "/c echo hello",
                Directory.GetCurrentDirectory(),
                s => lines.Add(s));

            CollectionAssert.Contains(lines, "[out] hello");
        }

        [TestMethod]
        public async Task RunProcessCheckedAsync_CapturesStandardError()
        {
            var lines = new List<string>();

            var ex = await Assert.ThrowsAsync<InvalidOperationException>(async () =>
            {
                await ProcessHandler.RunProcessCheckedAsync(
                    "cmd.exe",
                    "/c echo error-message 1>&2 && exit 1",
                    Directory.GetCurrentDirectory(),
                    s => lines.Add(s));
            });

            Assert.IsTrue(lines.Any(x => x.Contains("[err] error-message")));
            StringAssert.Contains(ex.Message, "error-message");
        }
    }
}
