import math
import pathlib
import moderngl_window as mglw
from moderngl_window.capture.ffmpeg import FFmpegCapture
from moderngl_window.geometry import quad_fs
import moderngl as mgl
import numpy as np
import imgui
from moderngl_window.integrations.imgui import ModernglWindowRenderer


def gen_data(N, size):
    r = 500
    angles = np.random.random(N) * 2 * np.pi
    dst = np.random.random(N) * r

    a = size[0] / 2 + np.cos(angles) * dst
    b = size[1] / 2 + np.sin(angles) * dst

    return np.c_[a, b, (np.pi + angles), np.empty(N)]


class SlimeConfig:
    N = 1_000_000
    move_speed = 50.0
    turn_speed = 50.0

    evaporation_speed = 5.0
    diffusion_speed = 10.0
    sensor_angle = 0.83
    sensor_size = 1
    sensor_distance = 10.0

    color1 = (1,1,1)
    color2 = (66/255, 135/255, 245/255)


class SlimeWindow(mglw.WindowConfig):
    title = "Slimes"
    gl_version = (4, 5)
    window_size = (1280, 720)
    resource_dir = (pathlib.Path(__file__).parent / "resources").resolve()
    map_size = (2560, 1440)
    aspect_ratio = None
    local_size = 1024
    vsync = False
    samples = 16

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        imgui.create_context()

        self.imgui = ModernglWindowRenderer(self.wnd)

        self.world_texture01 = self.ctx.texture(self.map_size, 1, dtype="f1")
        self.world_texture01.repeat_x, self.world_texture01.repeat_y = False, False
        self.world_texture01.filter = mgl.NEAREST, mgl.NEAREST

        self.world_texture02 = self.ctx.texture(self.map_size, 1, dtype="f1")
        self.world_texture02.repeat_x, self.world_texture02.repeat_y = False, False
        self.world_texture02.filter = mgl.NEAREST, mgl.NEAREST

        data = gen_data(SlimeConfig.N, self.map_size).astype("f4")
        self.slimes = self.ctx.buffer(data)  # each slime has a position and angle

        self.load_programs()

        self.update_uniforms()

        self.quad_fs = quad_fs(normals=False)
        
        self.videocapture = mglw.capture.FFmpegCapture(source=self.wnd.fbo)

    def restart_sim(self):
        self.world_texture01.release()
        self.world_texture02.release()

        self.world_texture01 = self.ctx.texture(self.map_size, 1, dtype="f1")
        self.world_texture01.repeat_x, self.world_texture01.repeat_y = False, False
        self.world_texture01.filter = mgl.NEAREST, mgl.NEAREST

        self.world_texture02 = self.ctx.texture(self.map_size, 1, dtype="f1")
        self.world_texture02.repeat_x, self.world_texture02.repeat_y = False, False
        self.world_texture02.filter = mgl.NEAREST, mgl.NEAREST

        data = gen_data(SlimeConfig.N, self.map_size).astype("f4")
        self.slimes.orphan(SlimeConfig.N * 4 * 4)
        self.slimes.write(data)

    def update_uniforms(self):
        self.blurr["diffuseSpeed"] = SlimeConfig.diffusion_speed
        self.blurr["evaporateSpeed"] = SlimeConfig.evaporation_speed

        self.compute_shader["moveSpeed"] = SlimeConfig.move_speed
        self.compute_shader["turnSpeed"] = SlimeConfig.turn_speed

        self.compute_shader["senorAngleSpacing"] = SlimeConfig.sensor_angle
        self.compute_shader["sensorDst"] = SlimeConfig.sensor_distance
        self.compute_shader["sensorSize"] = SlimeConfig.sensor_size

        self.render_program["color1"] = SlimeConfig.color1
        self.render_program["color2"] = SlimeConfig.color2

        self.compute_shader["N"] = SlimeConfig.N

    def load_programs(self):
        self.render_program = self.load_program("render_texture.glsl")
        self.render_program["texture0"] = 0
        self.compute_shader = self.load_compute_shader(
            "update.glsl",
            {
                "width": self.map_size[0],
                "height": self.map_size[1],
                "local_size": self.local_size,
            },
        )
        self.blurr = self.load_compute_shader("blur.glsl")

    def render(self, time: float, frame_time: float):
        self.world_texture01.use(0)
        self.quad_fs.render(self.render_program)

        self.world_texture01.bind_to_image(1, read=True, write=False)
        self.world_texture02.bind_to_image(0, read=False, write=True)
        self.slimes.bind_to_storage_buffer(2)

        # self.compute_shader["dt"] = frame_time
        # self.blurr["dt"] = frame_time

        group_size = int(math.ceil(SlimeConfig.N / self.local_size))
        self.compute_shader.run(group_size, 1, 1)

        self.world_texture01.bind_to_image(0, read=True, write=False)
        self.world_texture02.bind_to_image(1, read=True, write=True)
        self.blurr.run(self.map_size[0] // 16 + 1, self.map_size[1] // 16 + 1)

        self.world_texture01, self.world_texture02 = (
            self.world_texture02,
            self.world_texture01,
        )

        self.videocapture.save()

        self.render_ui()

    def render_ui(self):
        imgui.new_frame()
        if imgui.begin("Settings"):
            imgui.push_item_width(imgui.get_window_width() * 0.33)
            changed = False
            c, SlimeConfig.move_speed = imgui.slider_float(
                "Movement speed", SlimeConfig.move_speed, 0.5, 50
            )
            changed = changed or c
            c, SlimeConfig.turn_speed = imgui.slider_float(
                "Turn speed",
                SlimeConfig.turn_speed,
                0.5,
                50,
            )
            changed = changed or c
            c, SlimeConfig.evaporation_speed = imgui.slider_float(
                "Evaporation speed", SlimeConfig.evaporation_speed, 0.1, 20
            )
            changed = changed or c
            c, SlimeConfig.diffusion_speed = imgui.slider_float(
                "Diffusion speed",
                SlimeConfig.diffusion_speed,
                0.1,
                20,
            )
            changed = changed or c
            c, SlimeConfig.sensor_angle = imgui.slider_float(
                "Sensor-angle",
                SlimeConfig.sensor_angle,
                0,
                np.pi,
            )
            changed = changed or c
            c, SlimeConfig.sensor_size = imgui.slider_int(
                "Sensor-size",
                SlimeConfig.sensor_size,
                1,
                3,
            )
            changed = changed or c
            c, SlimeConfig.sensor_distance = imgui.slider_int(
                "Sensor distance",
                SlimeConfig.sensor_distance,
                1,
                25,
            )
            changed = changed or c
            if changed:
                self.update_uniforms()
            imgui.pop_item_width()

        imgui.end()

        if imgui.begin("Appearance"):
            imgui.push_item_width(imgui.get_window_width() * 0.33)
            changed_c1, SlimeConfig.color1 = imgui.color_edit3(
                "Color1", *SlimeConfig.color1
            )
            changed_c2, SlimeConfig.color2 = imgui.color_edit3(
                "Color2", *SlimeConfig.color2
            )
            if changed_c1 or changed_c2:
                self.update_uniforms()

        imgui.end()

        if imgui.begin("Actions"):
            imgui.push_item_width(imgui.get_window_width() * 0.33)
            changed, SlimeConfig.N = imgui.input_int(
                "Number of Slimes", SlimeConfig.N, step=1024, step_fast=2**15
            )
            SlimeConfig.N = min(max(2048, SlimeConfig.N), 2**24)
            if imgui.button("Restart Slimes"):
                self.restart_sim()

            imgui.pop_item_width()

        imgui.end()
        imgui.render()
        self.imgui.render(imgui.get_draw_data())

    def resize(self, width: int, height: int):
        self.imgui.resize(width, height)

    def key_event(self, key, action, modifiers):
        keys = self.wnd.keys
        if action == keys.ACTION_PRESS and key == keys.R:
            self.videocapture.start_capture(
                filename="video.mp4",
                framerate=30
            )
        if action == keys.ACTION_PRESS and key == keys.F:
            self.videocapture.release()
        self.imgui.key_event(key, action, modifiers)

    def mouse_position_event(self, x, y, dx, dy):
        self.imgui.mouse_position_event(x, y, dx, dy)

    def mouse_drag_event(self, x, y, dx, dy):
        self.imgui.mouse_drag_event(x, y, dx, dy)

    def mouse_scroll_event(self, x_offset, y_offset):
        self.imgui.mouse_scroll_event(x_offset, y_offset)

    def mouse_press_event(self, x, y, button):
        self.imgui.mouse_press_event(x, y, button)

    def mouse_release_event(self, x: int, y: int, button: int):
        self.imgui.mouse_release_event(x, y, button)

    def unicode_char_entered(self, char):
        self.imgui.unicode_char_entered(char)


SlimeWindow.run()
