using System;
using System.Collections.Generic;
using System.Text;

namespace SMMPI.Infrastructure.Plugins.Tools
{
    public static class SolutionRoot
    {
        // Cache the solution root directory once.
        private static string _solutionRoot;

        public static string Get()
        {
            if (_solutionRoot != null) return _solutionRoot;

            string startDir = Path.GetDirectoryName(System.Reflection.Assembly.GetExecutingAssembly().Location);

            var dir = new DirectoryInfo(startDir);
            while (dir != null)
            {
                // Check if this is the SMMPI solution root (or contains .sln)
                if (dir.Name == "SMMPI" || dir.GetFiles("*.sln").Length > 0)
                {
                    _solutionRoot = dir.FullName;
                    break;
                }

                dir = dir.Parent;
            }

            // Fallback: use current directory if we didn’t find it.
            if (_solutionRoot == null)
                _solutionRoot = Environment.CurrentDirectory;

            return _solutionRoot;
        }

        public static string ToSolutionAbsolutePath(string relativePath)
        {
            return Path.GetFullPath(Path.Combine(Get(), relativePath));
        }
    }
}
