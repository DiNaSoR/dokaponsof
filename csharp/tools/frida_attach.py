"""Frida: dump Parts data when accessed. Restart game and attach immediately."""
import frida, sys, os, time, struct

LOG = os.path.join(os.path.dirname(__file__), 'frida_trace.log')

JS = """
var base = null;
var mods = Process.enumerateModules();
for (var i = 0; i < mods.length; i++) {
    if (mods[i].name.indexOf('DOKAPON') !== -1) {
        base = mods[i].base;
        send('Game base: ' + base);
        break;
    }
}

var k32 = Process.getModuleByName('KERNEL32.dll');
Interceptor.attach(k32.getExportByName('CreateFileW'), {
    onEnter: function(args) {
        try {
            var p = args[0].readUtf16String();
            if (p && (p.indexOf('.spranm') !== -1 || p.indexOf('.txd') !== -1)) {
                send('[FILE] ' + p);
            }
        } catch(e) {}
    }
});

if (base) {
    // Hook section name copy
    try {
        Interceptor.attach(base.add(0x43720), {
            onEnter: function(args) {
                try {
                    var s = args[2].readUtf8String();
                    if (s && s.length > 0 && s.length < 40) {
                        send('[SECTION] ' + s);
                    }
                } catch(e) {}
            }
        });
    } catch(e) {}

    // Hook Parts-2 and dump the data being read
    try {
        Interceptor.attach(base.add(0x17506E), {
            onEnter: function(args) {
                var rbx = this.context.rbx;
                // Read 160 bytes: should cover section header + first entries
                var buf = rbx.readByteArray(160);
                send('[PARTS-DATA]', buf);
            }
        });
    } catch(e) {}

    // Also hook Parts-1
    try {
        Interceptor.attach(base.add(0x167C8E), {
            onEnter: function(args) {
                var rbx = this.context.rbx;
                var buf = rbx.readByteArray(160);
                send('[PARTS-DATA-1]', buf);
            }
        });
    } catch(e) {}
}

send('READY - navigate in game');
"""

log_f = open(LOG, 'w')

def on_msg(msg, data):
    if msg['type'] == 'send':
        line = msg['payload']
        print(line)
        log_f.write(line + '\n')
        if data and len(data) >= 32:
            hex_str = ' '.join(f'{b:02x}' for b in data[:160])
            print(f'  HEX: {hex_str}')
            log_f.write(f'  HEX: {hex_str}\n')
            # Parse as ASCII name (first 20 bytes) + uint32 totalSize + uint32 count
            name = data[:20].decode('ascii', errors='replace').rstrip('\x00 ')
            if len(data) >= 28:
                total_sz, count = struct.unpack_from('<II', data, 20)
                print(f'  Name: "{name}" totalSize={total_sz} count={count}')
                log_f.write(f'  Name: "{name}" totalSize={total_sz} count={count}\n')
                # If it's Parts, dump entries as 8 floats each
                if 'Parts' in name and count > 0 and len(data) >= 28 + 32:
                    for i in range(min(count, 3)):
                        off = 28 + i * 32
                        if off + 32 <= len(data):
                            vals = struct.unpack_from('<8f', data, off)
                            print(f'  Entry[{i}]: offXY=({vals[0]:.1f},{vals[1]:.1f}) sz=({vals[2]:.1f},{vals[3]:.1f}) uv=({vals[4]:.4f},{vals[5]:.4f})-({vals[6]:.4f},{vals[7]:.4f})')
                            log_f.write(f'  Entry[{i}]: offXY=({vals[0]:.1f},{vals[1]:.1f}) sz=({vals[2]:.1f},{vals[3]:.1f}) uv=({vals[4]:.4f},{vals[5]:.4f})-({vals[6]:.4f},{vals[7]:.4f})\n')
        log_f.flush()
    else:
        err = msg.get('description', str(msg))
        print(f'[ERR] {err}')
        log_f.write(f'[ERR] {err}\n')

device = frida.get_local_device()
target = None
for p in device.enumerate_processes():
    if 'DOKAPON' in p.name:
        target = p; break

if not target:
    print("Game not running! Start it, then run this."); sys.exit(1)

print(f"Attaching to PID {target.pid}... Log: {LOG}")
session = frida.attach(target.pid)
script = session.create_script(JS)
script.on('message', on_msg)
script.load()
print("Tracing 60s... navigate in game!\n")

time.sleep(60)
session.detach()
log_f.close()
print(f"\nDone. Log: {LOG}")
