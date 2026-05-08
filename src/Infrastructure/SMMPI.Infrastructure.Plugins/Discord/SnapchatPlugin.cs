using SMMPI.Domain.Entities;
using SMMPI.Domain.Interfaces;
using SMMPI.Infrastructure.Plugins.Tools;
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Text;

namespace SMMPI.Infrastructure.Plugins.Discord
{
    public class SnapchatPlugin : IPlatformPlugin
    {
        public string PlatformName => "Snapchat";

        public async void connect(string device_id)
        {
            string slnRoot = SolutionRoot.Get();
            string packageDir = Path.Combine(slnRoot, "./packages/old/Project/VCAM_GUI-master(3)/VCAM_GUI-master/");
            string scriptPath = Path.Combine(packageDir, "main.py");

            if (!File.Exists(scriptPath))
            {
                throw new FileNotFoundException($"Python script not found: {scriptPath}");
            }

            await ProcessHandler.RunProcessCheckedAsync(
                "python",
                $"-u \"{scriptPath}\"",
                packageDir);
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
