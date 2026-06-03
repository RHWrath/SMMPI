using SMMPI.Infrastructure.Plugins.Tools;
using System;
using System.Collections.Generic;
using System.Text;

namespace Teststraat
{
    [TestClass]
    public class SolutionRootTests
    {
        [TestMethod]
        public void CheckDirectoryExistsAndCreate_WhenDirectoryDoesNotExist_CreatesDirectory()
        {
            string tempPath = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString());

            try
            {
                Assert.IsFalse(Directory.Exists(tempPath));

                SolutionRoot.checkDirectoryExistsAndCreate(tempPath);

                Assert.IsTrue(Directory.Exists(tempPath));
            }
            finally
            {
                if (Directory.Exists(tempPath))
                    Directory.Delete(tempPath, true);
            }
        }

        [TestMethod]
        public void CheckDirectoryExistsAndCreate_WhenDirectoryAlreadyExists_DoesNotThrow()
        {
            string tempPath = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString());

            Directory.CreateDirectory(tempPath);

            try
            {
                SolutionRoot.checkDirectoryExistsAndCreate(tempPath);

                Assert.IsTrue(Directory.Exists(tempPath));
            }
            finally
            {
                if (Directory.Exists(tempPath))
                    Directory.Delete(tempPath, true);
            }
        }

        [TestMethod]
        public void Get_ReturnsNonEmptyPath()
        {
            string result = SolutionRoot.Get();

            Assert.IsFalse(string.IsNullOrWhiteSpace(result));
            Assert.IsTrue(Directory.Exists(result));
        }

        [TestMethod]
        public void Get_ReturnsSameValue_OnMultipleCalls()
        {
            string first = SolutionRoot.Get();
            string second = SolutionRoot.Get();

            Assert.AreEqual(first, second);
        }
    }
}
