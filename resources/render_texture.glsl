#version 430

#if defined VERTEX_SHADER

in vec3 in_position;
in vec2 in_texcoord_0;
out vec2 uv;

void main() {
    gl_Position = vec4(in_position, 1.0);
    uv = in_texcoord_0;
}

#elif defined FRAGMENT_SHADER


uniform sampler2D texture0;
out vec4 fragColor;
in vec2 uv;

uniform vec3 color1;
uniform vec3 color2;

void main() {
    vec3 c = mix(color1, color2, texture(texture0, uv).r);
    fragColor = vec4(c, 1.);
}

#endif