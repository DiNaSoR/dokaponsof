"""Frida: deep trace of sprite struct reading and draw calls."""
import frida, sys, os, struct, time

LOG = os.path.join(os.path.dirname(__file__), 'frida_trace.log')

JS = r"""
var base = null;
var mods = Process.enumerateModules();
for (var i = 0; i < mods.length; i++) {
    if (mods[i].name.indexOf('DOKAPON') !== -1) {
        base = mods[i].base;
        send('Game base: ' + base);
        break;
    }
}

if (!base) { send('ERROR: no game module'); }

var k32 = Process.getModuleByName('KERNEL32.dll');

// Track file opens
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
    // Hook section name copy at +0x43720 to see ALL section names being parsed
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

    // Hook D3D11 DrawIndexed to count draw calls per frame
    var d3d11 = Process.getModuleByName('d3d11.dll');
    if (d3d11) {
        send('d3d11 at ' + d3d11.base);
    }

    // Hook the Parts-2 data read at +0x17506E
    // This time dump MORE data - the full Sprite struct being processed
    var partsHitCount = 0;
    Interceptor.attach(base.add(0x17506E), {
        onEnter: function(args) {
            partsHitCount++;
            if (partsHitCount > 200) return; // limit spam

            var rbx = this.context.rbx;
            var rdi = this.context.rdi;
            var rsi = this.context.rsi;
            var r12 = this.context.r12;
            var r13 = this.context.r13;
            var r14 = this.context.r14;
            var r15 = this.context.r15;

            // Dump rbx data (160 bytes)
            try {
                var d = rbx.readByteArray(256);
                send('[PARTS-2-DUMP]', d);
            } catch(e) {}

            // Also dump what rdi/rsi/r12-r15 point to (might be sprite structs)
            var regs = {rdi: rdi, rsi: rsi, r12: r12, r13: r13, r14: r14, r15: r15};
            for (var name in regs) {
                try {
                    var ptr = regs[name];
                    if (ptr && !ptr.isNull() && ptr.compare(base) > 0) {
                        var rd = ptr.readByteArray(64);
                        send('[REG-' + name + ']', rd);
                    }
                } catch(e) {}
            }
        }
    });

    // Also hook Parts-1 at +0x167C8E
    var parts1Count = 0;
    Interceptor.attach(base.add(0x167C8E), {
        onEnter: function(args) {
            parts1Count++;
            if (parts1Count > 200) return;

            var rbx = this.context.rbx;
            try {
                var d = rbx.readByteArray(256);
                send('[PARTS-1-DUMP]', d);
            } catch(e) {}
        }
    });

    send('All hooks ready. Interact with game to trigger sprites.');
}
"""

log_f = open(LOG, 'w')
dump_count = 0

def on_msg(msg, data):
    global dump_count
    if msg['type'] == 'send':
        line = msg['payload']
        print(line)
        log_f.write(line + '\n')

        if data and len(data) >= 28:
            dump_count += 1
            hex_str = ' '.join(f'{b:02x}' for b in data[:min(256, len(data))])
            log_f.write(f'  HEX[{len(data)}]: {hex_str}\n')

            # Try to interpret as section header
            name = data[:20].decode('ascii', errors='replace').rstrip('\x00 ')
            if len(data) >= 28:
                val1, val2 = struct.unpack_from('<II', data, 20)
                log_f.write(f'  Header: name="{name}" field1={val1}(0x{val1:X}) field2={val2}(0x{val2:X})\n')

                # If it looks like Parts section, parse float entries
                if 'Parts' in name and val2 > 0:
                    count = val2
                    log_f.write(f'  Parts entries (count={count}):\n')
                    for i in range(min(count, 5)):
                        off = 28 + i * 32
                        if off + 32 <= len(data):
                            vals = struct.unpack_from('<8f', data, off)
                            log_f.write(f'    [{i}] off=({vals[0]:.1f},{vals[1]:.1f}) sz=({vals[2]:.1f},{vals[3]:.1f}) uv=({vals[4]:.4f},{vals[5]:.4f},{vals[6]:.4f},{vals[7]:.4f})\n')
                            print(f'  Parts[{i}] off=({vals[0]:.1f},{vals[1]:.1f}) sz=({vals[2]:.1f},{vals[3]:.1f}) uv=({vals[4]:.4f},{vals[5]:.4f},{vals[6]:.4f},{vals[7]:.4f})')

                # If Sprite section, parse sprite entries
                if name == 'Sprite' and val2 > 0:
                    count = val2
                    log_f.write(f'  Sprite entries (count={count}):\n')
                    for i in range(min(count, 5)):
                        off = 28 + i * 32
                        if off + 32 <= len(data):
                            pi, unk, ti = struct.unpack_from('<III', data, off)
                            px, py = struct.unpack_from('<ii', data, off + 12)
                            sx, sy, unk2 = struct.unpack_from('<fff', data, off + 20)
                            log_f.write(f'    [{i}] parts={pi} tex={ti} pos=({px},{py}) scale=({sx:.4f},{sy:.4f})\n')
                            print(f'  Sprite[{i}] parts={pi} tex={ti} pos=({px},{py}) scale=({sx:.4f},{sy:.4f})')

                # If Sequence, parse
                if 'Sequence' in name and val2 > 0:
                    count = val2
                    for i in range(min(count, 5)):
                        off = 28 + i * 20
                        if off + 20 <= len(data):
                            gi, dur, flags = struct.unpack_from('<III', data, off)
                            log_f.write(f'    Seq[{i}] group={gi} dur={dur} flags={flags}\n')

            if dump_count <= 20:
                # Print first 64 bytes hex for quick view
                short_hex = ' '.join(f'{b:02x}' for b in data[:64])
                print(f'  {short_hex}')

        log_f.flush()
    else:
        err = msg.get('description', str(msg))
        print(f'[ERR] {err}')

device = frida.get_local_device()
target = None
for p in device.enumerate_processes():
    if 'DOKAPON' in p.name:
        target = p; break

if not target:
    print("Game not running!"); sys.exit(1)

print(f"Attaching to PID {target.pid}... Log: {LOG}")
session = frida.attach(target.pid)
script = session.create_script(JS)
script.on('message', on_msg)
script.load()
print("Deep tracing 45s... interact with the game!\n")

time.sleep(45)
session.detach()
log_f.close()
print(f"\nDone. {dump_count} dumps captured. Log: {LOG}")
