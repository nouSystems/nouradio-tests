#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2024 nou Systems, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#


import numpy as np
from gnuradio import gr
try:
    import mss
    MSS_PRESENT = True
except ImportError:
    print("Warning: Screenshot functionality is not available without 'mss'; disabling screenshots.")
    MSS_PRESENT = False

class screenshot(gr.sync_block):
    """Take timed screenshots
    """
    def __init__(self,
                 dtype="complex",
                 test_name_filter=".*",
                 delay_samples=1000,
                 period_samples=-1,
                 auto_crop=True,
                 crop=[0,0,1,1],
                 monitor=1,
                 parent = None):
        """Take timed screenshots

        Args:
            dtype (str, optional): The string type of the incoming stream. Defaults to "complex".
            test_name_filter (str, optional): When running automated tests, filter which tests trigger this stop. Defaults to ".*" (all tests).
            delay_samples (int, optional): Take the first screenshot after this count of samples. Defaults to 1000.
            period_samples (int, optional): After the first screenshot, take screenshots ever N samples.
                Multiple screenshots will be produced if the multiple triggers occur within one buffer. Defaults to -1.
            auto_crop (bool, optional): Automatically crop the screenshots to the Qt Widget. Defaults to True.
            crop (list, optional): A normalized screen position for the screenshot in the form [top left x, top left y, width, height]. Ignored when auto_crop = True. Defaults to [0,0,1,1].
            monitor (int, optional): An integer 1-N for which monitor to use for screenshots.  Ignored when auto_crop = True.  Defaults to 1.
            parent (QWidget, optional): The parent widget for cropping the screenshot. Defaults to None.
        """
        TYPE_MAP = {"complex": np.complex64,
                    "float": np.float32,
                    "int": np.int32,
                    "short": np.int16,
                    "byte": np.int8}
        
        assert(dtype in TYPE_MAP)

        gr.sync_block.__init__(self,
            name="screenshot",
            in_sig=[TYPE_MAP[dtype]],
            out_sig=None)
        
        self.test_name_filter = test_name_filter

        self.delay_samples = np.ulonglong(delay_samples)
        self.period_samples = np.ulonglong(period_samples) if period_samples > 0 else None
        self.auto_crop = auto_crop
        self.crop = crop
        self.parent = parent
        self.monitor = monitor

        self.total_samples_passed = np.ulonglong(0)
        self.trigger_count = 0
        self.next_trigger_time_samples = self.delay_samples

    def get_window_geometry(self):
        # Get the window size of the flowgraph GUI in pixels
        # [left, top, width, height]
        # Use geometry() to avoid the window frame
        geo = self.parent.geometry()
        return [geo.x(), geo.y(), geo.width(), geo.height()]

    def get_crop_px(self):
        """
        Return the desired screenshot crop in the following form:
        [
            {left_px:   float},
            {top_px:    float},
            {width_px:  float},
            {height_px: float},
        ]
        _px values are in pixels
        """
        
        if not self.auto_crop or self.parent is None:
            window_crop_normalized = self.crop
            with mss.mss() as sct:
                screen_size_px = sct.monitors[self.monitor]
            window_crop_px = [
                window_crop_normalized[0] * screen_size_px["width"],
                window_crop_normalized[1] * screen_size_px["height"],
                window_crop_normalized[2] * screen_size_px["width"],
                window_crop_normalized[3] * screen_size_px["height"],
            ]
        else:
            window_crop_px = self.get_window_geometry()
            
        return window_crop_px
        
    def take_screenshot(self, name: str, crop_px: list):
        if MSS_PRESENT:
            with mss.mss() as sct:
                # The screen part to capture
                monitor = {
                    "left":   crop_px[0],
                    "top":    crop_px[1],
                    "width":  crop_px[2],
                    "height": crop_px[3]
                    }
                output = f"screenshot_{name}.png"

                # Grab the data
                sct_img = sct.grab(monitor)

                # Save to the picture file
                mss.tools.to_png(sct_img.rgb, sct_img.size, output=output)
        else:
            print("Warning: Screenshots are unavailable without the 'mss' package!")

    def should_trigger(self, ending_sample_count: bool) -> bool:
        """Do we need to take a screenshot now?

        Args:
            ending_sample_count (bool): When is the next screenshot time (in samples)?

        Returns:
            bool: True if it is time totake a screenshot, False otherwise
        """
        # If we are not repeating and have already triggered, do not trigger again
        if self.period_samples is None and self.trigger_count > 0:
            return False
        # Otherwise, check if we should be triggering this interval
        if self.next_trigger_time_samples <= ending_sample_count:
            return True
        # No trigger
        return False

    def advance_trigger(self):
        """For periodic triggers, advance the triggering by one cycle
        """
        self.trigger_count += 1
        
        if self.period_samples is not None:
            self.next_trigger_time_samples += self.period_samples

    def work(self, input_items, output_items):
        """If it is time to take a screenshot, take it.  Always take one screenshot per interval
        even if multiple triggers occur within one buffer's worth of samples.
        """
        self.total_samples_passed += len(input_items[0])

        crop_px = None
        while self.should_trigger(self.total_samples_passed):
            # Only calculate the crop parameters once per update.  Then just reuse them.
            if crop_px is None:
                crop_px = self.get_crop_px()
            self.take_screenshot(f"{self.next_trigger_time_samples}", crop_px)
            self.advance_trigger()

        return len(input_items[0])
