using SMMPI.Domain.Entities;
using SMMPI.Domain.Interfaces;
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Text;

namespace SMMPI.Infrastructure.Plugins.Discord
{
    public class SnapchatPlugin : IPlatformPlugin
    {
        public string PlatformName => "Snapchat";

        public void connect(string device_id)
        {
            string slnRoot = Tools.SolutionRoot.Get();
            string packageDir = Path.Combine(slnRoot, "./packages/old/Project/VCAM_GUI-master(3)/VCAM_GUI-master/");
            string scriptPath = Path.Combine(packageDir, "main.py");

            if (!File.Exists(scriptPath))
            {
                throw new FileNotFoundException($"Python script not found: {scriptPath}");
            }

            var processInfo = new System.Diagnostics.ProcessStartInfo
            {
                FileName = "python",
                Arguments = $"-u \"{scriptPath}\"",
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = false
            };

            var process = new Process();
            process.StartInfo = processInfo;

            process.OutputDataReceived += (_, e) =>
            {
                if (!string.IsNullOrWhiteSpace(e.Data))
                    Console.WriteLine("[PY] " + e.Data);
            };

            process.ErrorDataReceived += (_, e) =>
            {
                if (!string.IsNullOrWhiteSpace(e.Data))
                    Console.WriteLine("[PY-ERR] " + e.Data);
            };

            process.Start();
            process.BeginOutputReadLine();
            process.BeginErrorReadLine();
        }

        public void SendMessage(Payload payload)
        {
            throw new NotImplementedException();
        }

        public void SendMessage(Payload payload, string mediaFilepath)
        {
            throw new NotImplementedException();
        }
    }
}
