using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Windows.Forms;

// Shop Cleaning Simulator - native Windows launcher.
// The game's HTML is embedded inside this .exe as a resource. On launch it is
// written to a temp folder and opened in a chromeless Microsoft Edge "app"
// window (Chromium / WebView2 engine), so it looks and feels like a native app.
static class Program
{
    [STAThread]
    static void Main()
    {
        string htmlPath;
        try
        {
            // Extract the embedded HTML to a stable temp location.
            string dir = Path.Combine(Path.GetTempPath(), "ShopCleaningSimulator");
            Directory.CreateDirectory(dir);
            htmlPath = Path.Combine(dir, "shop-cleaning-simulator.html");

            var asm = Assembly.GetExecutingAssembly();
            using (Stream s = asm.GetManifestResourceStream("game.html"))
            using (var fs = new FileStream(htmlPath, FileMode.Create, FileAccess.Write))
            {
                if (s == null) throw new Exception("Embedded game resource missing.");
                s.CopyTo(fs);
            }
        }
        catch (Exception ex)
        {
            MessageBox.Show("Could not prepare the game files:\n\n" + ex.Message,
                "Shop Cleaning Simulator", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return;
        }

        string fileUrl = new Uri(htmlPath).AbsoluteUri;

        // Find Edge (Chromium). It powers a clean, modern, chromeless window.
        string edge = FindEdge();
        if (edge != null)
        {
            string profile = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "ShopCleaningSimulator", "win");
            try { Directory.CreateDirectory(profile); } catch { }

            var psi = new ProcessStartInfo
            {
                FileName = edge,
                UseShellExecute = false,
                Arguments =
                    "--app=\"" + fileUrl + "\"" +
                    " --window-size=1200,860" +
                    " --user-data-dir=\"" + profile + "\"" +
                    " --no-first-run --no-default-browser-check" +
                    " --disable-features=msEdgeWelcomePage,Translate,msSmartScreen" +
                    " --allow-file-access-from-files"
            };
            try { Process.Start(psi); return; }
            catch { /* fall through to default browser */ }
        }

        // Fallback: open in the user's default browser.
        try
        {
            Process.Start(new ProcessStartInfo(htmlPath) { UseShellExecute = true });
        }
        catch (Exception ex)
        {
            MessageBox.Show("Could not launch the game:\n\n" + ex.Message,
                "Shop Cleaning Simulator", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    static string FindEdge()
    {
        string[] paths =
        {
            @"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            @"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        };
        foreach (var p in paths)
            if (File.Exists(p)) return p;

        // Registry App Paths as a last resort.
        try
        {
            using (var k = Microsoft.Win32.Registry.LocalMachine.OpenSubKey(
                @"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe"))
            {
                if (k != null)
                {
                    var v = k.GetValue(null) as string;
                    if (!string.IsNullOrEmpty(v) && File.Exists(v)) return v;
                }
            }
        }
        catch { }
        return null;
    }
}
