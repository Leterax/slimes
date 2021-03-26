#version 450

// Update and move all slimes. Then lay down fermones onto world texture

#define width 0
#define height 0
#define local_size 1

#define PI 3.141592653

layout (local_size_x = local_size, local_size_y = 1, local_size_z = 1) in;

layout(r8, location=0) restrict writeonly uniform image2D destTex;
layout(r8, location=1) restrict readonly uniform image2D fromTex;

struct Slime {
    float x, y, angle, padding;
};

layout(std430, binding=2) restrict buffer inslimes {
    Slime slimes[];
} SlimeBuffer;

uniform int N;

uniform float dt;
uniform float moveSpeed;
uniform float senorAngleSpacing;
uniform float sensorDst;
uniform float turnSpeed;
uniform int sensorSize;


float rand(vec2 co){
    return fract(sin(dot(co.xy ,vec2(12.9898,78.233))) * 43758.5453);
}

void drawSlime(Slime slime) {
    imageStore(destTex, ivec2(slime.x, slime.y), vec4(1.));
}

float sense(Slime slime, float sensorAngleOffset) {
    float sensorAngle = slime.angle + sensorAngleOffset;
    vec2 sensorDir = vec2(cos(sensorAngle), sin(sensorAngle));
    ivec2 sensorCentre = ivec2(slime.x, slime.y) + ivec2(sensorDir * sensorDst);
    
    float sum = 0;
    for (int offsetX = -sensorSize; offsetX <= sensorSize; offsetX++) {
        for (int offsetY = -sensorSize; offsetY <= sensorSize; offsetY++) {
            ivec2 pos = sensorCentre + ivec2(offsetX, offsetY);

            if (pos.x >= 0 && pos.x < width && pos.y >=0 && pos.y < height) {
                sum += imageLoad(fromTex, pos).r;
            }
        }
    }
    return sum;

}

void main() {
    int index = int(gl_GlobalInvocationID);
    if (index >= N) {return;}
    Slime slime = SlimeBuffer.slimes[index];

    float weightForward = sense(slime, 0);
    float weightLeft = sense(slime, senorAngleSpacing);
    float weightRight = sense(slime, -senorAngleSpacing);

    float randomSteerStrength = rand(vec2(slime.x, slime.y)*dt*slime.angle);


    if (weightForward > weightLeft && weightForward > weightRight) {}
    else if (weightForward < weightLeft && weightForward < weightRight) {
        slime.angle += (randomSteerStrength - 0.5) * 2 * turnSpeed * dt;
    }
    else if (weightRight > weightLeft) {
        slime.angle -= randomSteerStrength * turnSpeed * dt;
    }
    else if (weightLeft > weightRight) {
        slime.angle += randomSteerStrength * turnSpeed * dt;
    }


    vec2 direction = vec2(cos(slime.angle), sin(slime.angle));
    vec2 newPos = vec2(slime.x, slime.y) + (direction * moveSpeed * dt);

    if (newPos.x < 0. || newPos.x >= width || newPos.y < 0. || newPos.y >= height) {
        newPos.x = min(width-0.01, max(0., newPos.x));
        newPos.y = min(height-0.01, max(0., newPos.y));
        slime.angle = rand(newPos) * 2 * PI;
    }
    slime.x = newPos.x;
    slime.y = newPos.y;
    drawSlime(slime);
    SlimeBuffer.slimes[index] = Slime(slime.x, slime.y, slime.angle, 0.);
}