// Discover devices through the installed monitor's own backend. No machine IDs are bundled.
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
const runtime = await import(GLib.filename_to_uri(ARGV[0] + '/services/runtime.js', null));
await runtime.refreshDiscovery();
const descriptors = [...runtime.getAmdGpuDescriptors(), ...runtime.getIntelGpuDescriptors()];
const devices = descriptors.map(gpu => ({version: 2, type: 'gpu', device: gpu.device,
    name: gpu.name, usage: Boolean(gpu.usagePath), memory: Boolean(gpu.memoryTotalPath), displayName: ''}));
const thermal = descriptors.filter(gpu => gpu.temperaturePath).map(gpu => ({version: 2,
    type: 'thermal-gpu', device: gpu.device, name: gpu.name, monitor: true}));
if (GLib.find_program_in_path('nvidia-smi')) {
    const proc = Gio.Subprocess.new(['nvidia-smi', '--query-gpu=uuid,name', '--format=csv,noheader'],
        Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE);
    const [ok, output] = proc.communicate_utf8(null, null);
    if (ok && proc.get_successful()) for (const line of output.trim().split('\n').filter(Boolean)) {
        const comma = line.indexOf(',');
        if (comma < 1) continue;
        const device = line.slice(0, comma).trim(), name = line.slice(comma + 1).trim();
        devices.push({version: 2, type: 'gpu', device, name, usage: true, memory: true, displayName: ''});
        thermal.push({version: 2, type: 'thermal-gpu', device, name, monitor: true});
    }
}
print(JSON.stringify({devices, thermal}));
