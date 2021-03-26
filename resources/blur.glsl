#version 450

// reduce fermones and blur fermones

layout (local_size_x = 16, local_size_y = 16) in;

layout(r8, location=0) restrict readonly uniform image2D fromTex;
layout(r8, location=1) uniform image2D destTex;

float fetchValue(ivec2 co) {
    return imageLoad(fromTex, co).r;
}

float blured(ivec2 co) {
    float sum = 
        fetchValue(co) +
        fetchValue(co + ivec2(-1, -1)) +
        fetchValue(co + ivec2( 0, -1)) +
        fetchValue(co + ivec2( 1, -1)) +
        fetchValue(co + ivec2( 1,  0)) +
        fetchValue(co + ivec2( 1,  1)) +
        fetchValue(co + ivec2( 0,  1)) +
        fetchValue(co + ivec2(-1,  1)) +
        fetchValue(co + ivec2(-1,  0));
    
    return sum / 9.;
}

uniform float dt;
uniform float diffuseSpeed;
uniform float evaporateSpeed;


void main() {
    ivec2 texelPos = ivec2(gl_GlobalInvocationID.xy);
    float original_value = imageLoad(fromTex, texelPos).r;
    float v = blured(texelPos);
    
    float diffused = mix(original_value, v, diffuseSpeed * dt);
    float evaporated = max(0, diffused - evaporateSpeed * dt);

    imageStore(destTex, texelPos, vec4(evaporated));
}
