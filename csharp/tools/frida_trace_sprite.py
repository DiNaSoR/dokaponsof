"""
Frida script to trace sprite rendering in DOKAPON! Sword of Fury.
Hooks the spranm section parser and texture creation to understand
how the EXE reads sprite position/part data.
"""
import frida
import sys
import subprocess
import time
import json

EXE_PATH = r"D:\Program Files (x86)\Steam\steamapps\common\DOKAPON ~Sword of Fury~\DOKAPON! Sword of Fury.exe"
EXE_DIR = r"D:\Program Files (x86)\Steam\steamapps\common\DOKAPON ~Sword of Fury~"

# From our static analysis:
# "Parts" string xref at 0x140167C4A (in a section name comparison function)
# "Texture" string xref at 0x14004271A
# The function at 0x140043720 is called right after loading section names
# Image base: 0x140000000

JS_HOOK = """
'use strict';

var base = Module.findBaseAddress('DOKAPON! Sword of Fury.exe');
if (!base) {
    // Try alternate name
    var mods = Process.enumerateModules();
    for (var i = 0; i < mods.length; i++) {
        if (mods[i].name.indexOf('DOKAPON') !== -1 || mods[i].name.indexOf('WindowsMain') !== -1) {
            base = mods[i].base;
            send({type: 'info', msg: 'Found module: ' + mods[i].name + ' at ' + base});
            break;
        }
    }
}

if (!base) {
    send({type: 'error', msg: 'Could not find game module'});
} else {
    send({type: 'info', msg: 'Game base: ' + base});

    // Hook the section name comparison function (0x140043720 - called after LEA of section names)
    // This function seems to be called with: rcx=object, rdx=buffer, r8=string_ptr
    var sectionCompare = base.add(0x43720);
    try {
        Interceptor.attach(sectionCompare, {
            onEnter: function(args) {
                try {
                    var namePtr = args[2];
                    if (namePtr && !namePtr.isNull()) {
                        var name = namePtr.readUtf8String();
                        if (name && (name.indexOf('Sprite') !== -1 || name.indexOf('Parts') !== -1 ||
                            name.indexOf('Sequence') !== -1 || name.indexOf('Texture') !== -1 ||
                            name.indexOf('Anime') !== -1 || name.indexOf('Convert') !== -1)) {
                            send({type: 'section', name: name, caller: this.returnAddress.sub(base).toString(16)});
                        }
                    }
                } catch(e) {}
            }
        });
        send({type: 'info', msg: 'Hooked section compare at ' + sectionCompare});
    } catch(e) {
        send({type: 'error', msg: 'Failed to hook section compare: ' + e.message});
    }

    // Hook file open to see which spranm files are loaded
    // Kernel::CFile::OpenFile or generic CreateFileW
    var createFileW = Module.findExportByName('KERNEL32.dll', 'CreateFileW');
    if (createFileW) {
        Interceptor.attach(createFileW, {
            onEnter: function(args) {
                try {
                    var path = args[0].readUtf16String();
                    if (path && (path.indexOf('.spranm') !== -1 || path.indexOf('.txd') !== -1)) {
                        send({type: 'file_open', path: path});
                    }
                } catch(e) {}
            }
        });
        send({type: 'info', msg: 'Hooked CreateFileW'});
    }

    // Hook D3D11 CreateTexture2D to see texture uploads
    var d3d11 = Module.findBaseAddress('d3d11.dll');
    if (d3d11) {
        send({type: 'info', msg: 'd3d11.dll at ' + d3d11});
    }

    // Monitor memory reads around sprite struct parsing
    // The "Parts" xref is at base+0x167C4A, inside a larger parser function
    // Let's find the function start and hook it

    // Hook at the Parts string reference location to capture the parsing context
    var partsRef1 = base.add(0x167C4A);
    try {
        Interceptor.attach(partsRef1, {
            onEnter: function(args) {
                send({type: 'parts_parse', msg: 'Parts section parsing triggered',
                      caller: this.returnAddress.sub(base).toString(16),
                      rsp: this.context.rsp.toString(16),
                      rbx: this.context.rbx.toString(16)});
                // Dump some context around the data being parsed
                try {
                    var rbx = this.context.rbx;
                    if (rbx && !rbx.isNull()) {
                        var nearby = rbx.readByteArray(64);
                        send({type: 'parts_data', data: Array.from(new Uint8Array(nearby))});
                    }
                } catch(e) {}
            }
        });
        send({type: 'info', msg: 'Hooked Parts parse at ' + partsRef1});
    } catch(e) {
        send({type: 'error', msg: 'Failed to hook Parts parse: ' + e.message});
    }

    // Hook the second Parts reference too
    var partsRef2 = base.add(0x17502A);
    try {
        Interceptor.attach(partsRef2, {
            onEnter: function(args) {
                send({type: 'parts_parse2', msg: 'Parts section parsing (2nd path)',
                      caller: this.returnAddress.sub(base).toString(16)});
                try {
                    var rbx = this.context.rbx;
                    if (rbx && !rbx.isNull()) {
                        var nearby = rbx.readByteArray(64);
                        send({type: 'parts_data2', data: Array.from(new Uint8Array(nearby))});
                    }
                } catch(e) {}
            }
        });
        send({type: 'info', msg: 'Hooked Parts parse 2 at ' + partsRef2});
    } catch(e) {
        send({type: 'error', msg: 'Failed to hook Parts parse 2: ' + e.message});
    }

    send({type: 'info', msg: 'All hooks installed. Play the game to see traces.'});
}
"""

def on_message(message, data):
    if message['type'] == 'send':
        payload = message['payload']
        msg_type = payload.get('type', 'unknown')

        if msg_type == 'file_open':
            print(f"[FILE] {payload['path']}")
        elif msg_type == 'section':
            print(f"[SECTION] '{payload['name']}' parsed (caller: 0x{payload['caller']})")
        elif msg_type == 'parts_parse' or msg_type == 'parts_parse2':
            print(f"[PARTS] {payload['msg']}")
        elif msg_type == 'parts_data' or msg_type == 'parts_data2':
            d = payload['data']
            hex_str = ' '.join(f'{b:02x}' for b in d[:48])
            print(f"  Data: {hex_str}")
        elif msg_type == 'info':
            print(f"[INFO] {payload['msg']}")
        elif msg_type == 'error':
            print(f"[ERROR] {payload['msg']}")
        else:
            print(f"[{msg_type}] {payload}")
    elif message['type'] == 'error':
        print(f"[FRIDA ERROR] {message.get('description', message)}")

def main():
    print("Starting DOKAPON! Sword of Fury with Frida instrumentation...")
    print("Will trace: file opens, section parsing, Parts/Sprite data reads")
    print("Press Ctrl+C to stop\n")

    try:
        # Spawn the game process
        pid = frida.spawn([EXE_PATH], cwd=EXE_DIR)
        print(f"Spawned process PID: {pid}")

        session = frida.attach(pid)
        print("Attached to process")

        script = session.create_script(JS_HOOK)
        script.on('message', on_message)
        script.load()
        print("Script loaded, resuming process...\n")

        frida.resume(pid)

        # Keep running until user presses Ctrl+C
        print("=" * 60)
        print("Game is running. Navigate to the title/intro screen.")
        print("Press Ctrl+C to stop tracing.")
        print("=" * 60 + "\n")

        sys.stdin.read()

    except KeyboardInterrupt:
        print("\nStopping trace...")
    except Exception as e:
        print(f"Error: {e}")
        print("\nIf Steam guard blocks the launch, try:")
        print("1. Launch the game normally first")
        print("2. Then run this script to attach to the running process")
    finally:
        try:
            frida.kill(pid)
        except:
            pass

if __name__ == '__main__':
    main()
