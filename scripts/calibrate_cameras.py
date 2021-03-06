#!/usr/bin/env python3
"""Script for generating the calibration data for the cameras and verifying the
 output.
"""

from trifinger_cameras.charuco_board_handler import CharucoBoardHandler
import trifinger_cameras.utils as utils
import argparse
import numpy as np
import cv2
import yaml


def calibrate_intrinsic_parameters(calibration_data, calibration_results_file):
    """Calibrate intrinsic parameters of the camera given different images
    taken for the Charuco board from different views, the resulting parameters
    are saved to the provided filename.

    Args:
        calibration_data (str):  directory of the stored images of the
        Charuco board.
        calibration_results_file (str):  filepath that will be used to write
        the calibration results in.
    """
    handler = CharucoBoardHandler()

    camera_matrix, dist_coeffs, error = handler.calibrate(
        calibration_data, visualize=False
    )
    camera_info = dict()
    camera_info["camera_matrix"] = dict()
    camera_info["camera_matrix"]["rows"] = 3
    camera_info["camera_matrix"]["cols"] = 3
    camera_info["camera_matrix"]["data"] = camera_matrix.flatten().tolist()
    camera_info["distortion_coefficients"] = dict()
    camera_info["distortion_coefficients"]["rows"] = 1
    camera_info["distortion_coefficients"]["cols"] = 5
    camera_info["distortion_coefficients"][
        "data"
    ] = dist_coeffs.flatten().tolist()

    with open(calibration_results_file, "w") as outfile:
        yaml.dump(
            camera_info, outfile, default_flow_style=False,
        )
    return


def calibrate_extrinsic_parameters(
    calibration_results_file,
    charuco_centralized_image_filename,
    extrinsic_calibration_filename,
    impose_cube=True,
):
    """Calibrate extrinsic parameters of the camera given one image taken for
        the Charuco board centered at (0, 0, 0) the resulting parameters are
        saved to the provided filename and a virtual cube is imposed on the
        board for verification.

        Args:
            calibration_results_file (str):  filepath that will be used to read
            the intrinsic calibration results.
            charuco_centralized_image_filename (str): filename of the image
            taken for the Charuco board centered at (0, 0, 0).
            extrinsic_calibration_filename (str):  filepath that will be used
            to write the extrinsic calibration results in.
            impose_cube (bool): boolean whether to output a virtual cube
            imposed on the first square of the board or not.
        """
    with open(calibration_results_file) as file:
        calibration_data = yaml.safe_load(file)

    def config_matrix(data):
        return np.array(data["data"]).reshape(data["rows"], data["cols"])

    camera_matrix = config_matrix(calibration_data["camera_matrix"])
    dist_coeffs = config_matrix(calibration_data["distortion_coefficients"])

    handler = CharucoBoardHandler(camera_matrix, dist_coeffs)

    rvec, tvec = handler.detect_board_in_image(
        charuco_centralized_image_filename, visualize=False
    )

    # projection_matrix = np.zeros((4, 4))
    projection_matrix = utils.rodrigues_to_matrix(rvec)
    projection_matrix[0:3, 3] = tvec[:, 0]
    projection_matrix[3, 3] = 1

    calibration_data["projection_matrix"] = dict()
    calibration_data["projection_matrix"]["rows"] = 4
    calibration_data["projection_matrix"]["cols"] = 4
    calibration_data["projection_matrix"][
        "data"
    ] = projection_matrix.flatten().tolist()

    with open(extrinsic_calibration_filename, "w") as outfile:
        yaml.dump(
            calibration_data, outfile, default_flow_style=False,
        )

    if impose_cube:
        new_object_points = (
            np.array(
                [
                    [0, 0, 0],
                    [0, 1, 0],
                    [1, 0, 0],
                    [1, 1, 0],
                    [0, 0, 1],
                    [0, 1, 1],
                    [1, 0, 1],
                    [1, 1, 1],
                ],
                dtype=np.float32,
            )
            * 0.04
        )
        point_pairs = (
            (0, 4),
            (1, 5),
            (2, 6),
            (3, 7),
            (0, 1),
            (0, 2),
            (1, 3),
            (2, 3),
            (4, 5),
            (4, 6),
            (5, 7),
            (6, 7),
        )

        img = cv2.imread(charuco_centralized_image_filename)
        imgpoints, _ = cv2.projectPoints(
            new_object_points, rvec, tvec, camera_matrix, dist_coeffs,
        )

        for p1, p2 in point_pairs:
            cv2.line(
                img,
                tuple(imgpoints[p1, 0]),
                tuple(imgpoints[p2, 0]),
                [200, 200, 0],
                thickness=2,
            )

        cv2.imshow("Imposed Cube", img)
        while cv2.waitKey(10) == -1:
            pass


def main():
    """Execute an action depending on arguments passed by the user."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=["intrinsic_calibration", "extrinsic_calibration"],
        help="""Action that is executed.""",
    )

    parser.add_argument(
        "--intrinsic_calibration_filename",
        type=str,
        help="""Filename used for saving intrinsic calibration
                        data or loading it""",
    )

    parser.add_argument(
        "--calibration_data",
        type=str,
        help="""Path to the calibration data directory (only
                        used for action 'intrinsic_calibration').""",
    )

    parser.add_argument(
        "--extrinsic_calibration_filename",
        type=str,
        help="""Filename used for saving intrinsic calibration
                         data.""",
    )
    parser.add_argument(
        "--image_view_filename",
        type=str,
        help="""Image with chruco centralized at the (0, 0, 0)
                        position.""",
    )

    args = parser.parse_args()

    if args.action == "intrinsic_calibration":
        if not args.intrinsic_calibration_filename:
            raise RuntimeError("intrinsic_calibration_filename not specified.")
        if not args.calibration_data:
            raise RuntimeError("calibration_data not specified.")
        calibrate_intrinsic_parameters(
            args.calibration_data, args.intrinsic_calibration_filename
        )
    elif args.action == "extrinsic_calibration":
        if not args.intrinsic_calibration_filename:
            raise RuntimeError("intrinsic_calibration_filename not specified.")
        if not args.extrinsic_calibration_filename:
            raise RuntimeError("extrinsic_calibration_filename not specified.")
        if not args.image_view_filename:
            raise RuntimeError("image_view_filename not specified.")
        calibrate_extrinsic_parameters(
            args.intrinsic_calibration_filename,
            args.image_view_filename,
            args.extrinsic_calibration_filename,
            impose_cube=True,
        )


if __name__ == "__main__":
    main()
