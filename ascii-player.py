#!/usr/bin/env python3

import curses
import math
import numpy
import os
import sys
import time
import yt_dlp
from ffpyplayer import pic
from ffpyplayer.player import MediaPlayer

ASCII_CHARS = " `.-':_,^=;><+!rc*/z?sLTv)J7(|Fi{C}fI31tlu[neoZ5Yxjya]2ESwqkP6h9d4VpOGbUAKXHm8RD#$Bg0MNWQ%&@"
CHAR_RATIO = 2.2


def rgb_to_curses_color(rgb):
    # Convert to 3 bits with a threshold of 1/3 of 255
    color = "".join(str(int(c / 85.3 > 1)) for c in rgb)
    if os.name == "posix":
        # *nix systems use BGR
        color = color[::-1]
    return curses.color_pair(int(color, 2) + 1) | curses.A_BOLD


def resize_image(img, max_width, max_height):
    width, height = img.get_size()
    new_width = max_width
    ratio = height / width / CHAR_RATIO
    new_height = new_width * ratio
    if new_height > max_height:
        ratio = max_width / new_height
        new_height = max_height
        new_width = new_height * ratio

    sws = pic.SWScale(width, height, img.get_pixel_format(),
                      ow=int(new_width), oh=math.floor(new_height))
    return sws.scale(img)


def main(screen, path, title):
    max_height, max_width = screen.getmaxyx()
    duration = None
    formatted_duration = None

    curses.curs_set(0)
    curses.use_default_colors()
    for i in range(0, 8):
        curses.init_pair(i + 1, i, -1)

    titlewin = curses.newwin(3, max_width, 0, 0)
    titlewin.box(0, 0)
    titlewin.move(1, 1)
    titlewin.addstr(title)
    titlewin.refresh()

    video = curses.newwin(max_height - 4, max_width - 1, 3, 0)
    max_vid_height, max_vid_width = video.getmaxyx()
    video.nodelay(True)
    video.keypad(True)

    barwin = curses.newwin(1, max_width, max_height - 1, 0)

    player = MediaPlayer(path)
    metadata = player.get_metadata()

    while True:
        frame, frame_length = player.get_frame()
        if frame_length == "paused":
            if video.getch() == ord(" "):
                player.set_pause(False)
                titlewin.move(1, max_width - 9)
                titlewin.addstr("        ")
                titlewin.refresh()
        elif frame_length == "eof":
            break
        elif frame is None:
            duration = metadata["duration"]
            if duration is not None:
                formatted_duration = time.strftime("%M:%S", time.gmtime(duration))
            time.sleep(0.01)
        else:
            frame_start = time.time()
            image = frame[0]
            image = resize_image(image, max_vid_width, max_vid_height)
            width, height = image.get_size()
            sws = pic.SWScale(width, height, image.get_pixel_format(), ofmt='gray')
            greyscale = sws.scale(image)
            # https://stackoverflow.com/a/59628167
            image_pixels = numpy.uint8(numpy.asarray(list(image.to_bytearray()[0]))
                                       .reshape(height, width, 3))
            greyscale_pixels = numpy.uint8(numpy.asarray(list(greyscale.to_bytearray()[0]))
                                           .reshape(height, width))

            video.move(0, 0)
            for row in range(height):
                for col in range(width):
                    char = ASCII_CHARS[int(greyscale_pixels[row, col] // 2.8)]
                    video.addch(char, rgb_to_curses_color(image_pixels[row, col]))
                video.move(row, 0)
            video.refresh()

            barwin.move(0, 0)
            bar_start = time.strftime("%M:%S", time.gmtime(player.get_pts())) + " ["
            bar_end = "] " + formatted_duration
            bar_width = width - len(bar_end) - len(bar_start)
            num = int(player.get_pts() / duration * bar_width)
            barwin.addstr(bar_start)
            for col in range(0, bar_width):
                if col > num:
                    barwin.addch("-")
                elif col == num:
                    barwin.addch("O")
                else:
                    barwin.addch("=")
            barwin.addstr(bar_end)
            barwin.refresh()

            key = video.getch()
            if key == ord("q"):
                # Exits frame loop
                break
            elif key == ord(" "):
                player.set_pause(True)
                titlewin.move(1, max_width - 9)
                titlewin.addstr("(Paused)")
                titlewin.refresh()
            elif key == curses.KEY_LEFT:
                player.seek(-5)
            elif key == curses.KEY_RIGHT:
                if player.get_pts() + 6 < duration:
                    player.seek(5)

            time.sleep(max(0, frame_length - (time.time() - frame_start)))


def fetch_youtube_video(url):
    print("Fetching YouTube video...")
    options = {
        "quiet": True,
        "simulate": True,
        "forceurl": True,
        "format": "w"
    }
    with yt_dlp.YoutubeDL(options) as ytdl:
        info = ytdl.extract_info(url, download=False)
    return (info.get("title"), info.get("url"))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        print("Colour ASCII video player\n")
        print("- Q: Quit\n- Space: Pasue\n- Left & right arrows: Seek\n")
        path = input("Path or URL: ")

    if "youtu" in path:
        yt_data = fetch_youtube_video(path)
        title = yt_data[0]
        path = yt_data[1]
    else:
        title = os.path.basename(path)

    curses.wrapper(main, path, title)
