####
# upip.install("picoweb")
# upip.install("micropython-ulogging")

# adapted from https://github.com/lemariva/uPyCam/blob/master/webcam.py

import network
import utime
import ntptime

import camera
import picoweb
import time
import uasyncio as asyncio


##### wifi connection
ssid = 'FiberHGW_TPCB86_2.4GHz'
password = 'cyHRjRXs'

def do_connect():
    sta_if = network.WLAN(network.STA_IF)
    start = utime.time()
    timed_out = False

    if not sta_if.isconnected():
        print('Aga baglaniliyor...')
        sta_if.active(True)
        sta_if.connect(ssid, password)
        while not sta_if.isconnected() and \
            not timed_out:        
            if utime.time() - start >= 20:
                timed_out = True
            else:
                pass

    if sta_if.isconnected():
        ntptime.settime()
        print('Baglanti saglandi: ', sta_if.ifconfig())
    else: 
        print('Baglanti yok!')


##### web app
app = picoweb.WebApp('app')

@app.route('/')
def index(req, resp):
    stream = True # single frame or stream
    
    if (not camera.init(0,
            d0=19, d1=22, d2=23, d3=21, d4=18, d5=26, d6=35, d7=34,
            href=39, vsync=36, reset=-1, sioc=25, siod=33, xclk=32, pclk=5, pwdn=-1,
            format=camera.JPEG, framesize=camera.FRAME_VGA, 
            xclk_freq=camera.XCLK_10MHz,fb_location=camera.PSRAM)):
        camera.deinit()
        await asyncio.sleep(1)
        # If we fail to init, return a 503
        if (not camera.init(0,
            d0=19, d1=22, d2=23, d3=21, d4=18, d5=26, d6=35, d7=34,
            href=39, vsync=36, reset=-1, sioc=25, siod=33, xclk=32, pclk=5, pwdn=-1,
            format=camera.JPEG, framesize=camera.FRAME_VGA, 
            xclk_freq=camera.XCLK_10MHz,fb_location=camera.PSRAM)):
                yield from picoweb.start_response(resp, status=503)
                yield from resp.awrite('HATA: Kamera baslatilamadi!\r\n\r\n')
                return
            
    # wait for sensor to start and focus before capturing image
    await asyncio.sleep(2)
    
    n_frame = 0
    while True:
        n_try = 0
        buf = False
        while (n_try < 10 and buf == False): #{
            # wait for sensor to start and focus before capturing image
            buf = camera.capture()
            if (buf == False): await asyncio.sleep(2)
            n_try = n_try + 1
    
        if (not stream):
            camera.deinit()    

        if (type(buf) is bytes and len(buf) > 0):
            try:
                if (not stream):
                    yield from picoweb.start_response(resp, "image/jpeg")
                    yield from resp.awrite(buf)
                    print('JPEG: Frame gonderildi')
                    break
            
                if (n_frame == 0): 
                    yield from picoweb.start_response(resp, "multipart/x-mixed-replace; boundary=myboundary")
            
                yield from resp.awrite('--myboundary\r\n')
                yield from resp.awrite('Content-Type:   image/jpeg\r\n')
                yield from resp.awrite('Content-length: ' + str(len(buf)) + '\r\n\r\n')
                yield from resp.awrite(buf)

            except:
                # Connection gone?
                print('Baglanti sonlandi!')
                camera.deinit()
                return

        else: 
            if (stream):
                camera.deinit()
        
            #picoweb.http_error(resp, 503)
            yield from picoweb.start_response(resp, status=503)
            if (stream and n_frame > 0): 
                yield from resp.awrite('Content-Type:   text/html; charset=utf-8\r\n\r\n')
            
            yield from resp.awrite('Hata:\r\n\r\n' + str(buf))
            return
        
        print('MJPEG: Gonderilen frame ' + str(n_frame))
        n_frame = n_frame + 1


def run():
    app.run(host='0.0.0.0', port=80, debug=True)


##### start
do_connect()
run()
