#!/usr/bin/env python3
"""
Play back TriCameraObservations from a log file.
"""
import argparse
import numpy as np
import cv2

import trifinger_cameras


def main():
    argparser = argparse.ArgumentParser(description=__doc__)
    argparser.add_argument(
        "filename", type=str, help="""Path to the log file.""",
    )
    args = argparser.parse_args()

    log_reader = trifinger_cameras.tricamera.LogReader(args.filename)

    # determine rate based on time stamps
    start_time = log_reader.data[0].cameras[0].timestamp
    end_time = log_reader.data[-1].cameras[0].timestamp
    interval = (end_time - start_time) / len(log_reader.data)
    # convert to ms
    interval = int(interval * 1000)

    print(
        "Loaded {} frames at an average interval of {} ms ({:.1f} fps)".format(
            len(log_reader.data), interval, 1000 / interval
        )
    )

    for observation in log_reader.data:
        window_60 = "Image Stream camera60"
        window_180 = "Image Stream camera180"
        window_300 = "Image Stream camera300"
        cv2.imshow(
            window_180, np.array(observation.cameras[0].image, copy=False)
        )
        cv2.imshow(
            window_300, np.array(observation.cameras[1].image, copy=False)
        )
        cv2.imshow(
            window_60, np.array(observation.cameras[2].image, copy=False)
        )

        # stop if either "q" or ESC is pressed
        if cv2.waitKey(interval) in [ord("q"), 27]:  # 27 = ESC
            break


if __name__ == "__main__":
    main()