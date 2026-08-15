// The orb Bruno shows while it is listening, thinking, or speaking.
//
// The fragment shader below is adapted from a community WebGL orb shader that
// circulated as a React component. The original author is not known to us; if
// you recognise it, please open an issue and we will credit you properly.
// Everything around it -- the WebGL setup, the state and level handling, the
// window -- is Bruno's.
//
// Plain WebGL, no libraries. The whole picture is one fragment shader painted
// over a single triangle that covers the viewport, so the usual reasons to
// reach for a 3D framework -- meshes, cameras, scene graphs -- do not apply.
// See docs/orb/README.md for what this was ported from and what changed.
//
// Nothing here reads a microphone. Levels arrive from the application, which
// already has the audio; opening a second stream would prompt for permission
// and claim a device Bruno is using.

'use strict';

const VERTEX_SHADER = `
precision highp float;
attribute vec2 position;
attribute vec2 uv;
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = vec4(position, 0.0, 1.0);
}
`;

// Carried over from the reference component almost unchanged. This is the
// design; the rest of this file exists to feed it.
const FRAGMENT_SHADER = `
precision highp float;

uniform float iTime;
uniform vec3 iResolution;
uniform float hue;
uniform float hover;
uniform float rot;
uniform float hoverIntensity;
uniform float opacity;
varying vec2 vUv;

vec3 rgb2yiq(vec3 c) {
  float y = dot(c, vec3(0.299, 0.587, 0.114));
  float i = dot(c, vec3(0.596, -0.274, -0.322));
  float q = dot(c, vec3(0.211, -0.523, 0.312));
  return vec3(y, i, q);
}

vec3 yiq2rgb(vec3 c) {
  float r = c.x + 0.956 * c.y + 0.621 * c.z;
  float g = c.x - 0.272 * c.y - 0.647 * c.z;
  float b = c.x - 1.106 * c.y + 1.703 * c.z;
  return vec3(r, g, b);
}

vec3 adjustHue(vec3 color, float hueDeg) {
  float hueRad = hueDeg * 3.14159265 / 180.0;
  vec3 yiq = rgb2yiq(color);
  float cosA = cos(hueRad);
  float sinA = sin(hueRad);
  float i = yiq.y * cosA - yiq.z * sinA;
  float q = yiq.y * sinA + yiq.z * cosA;
  yiq.y = i;
  yiq.z = q;
  return yiq2rgb(yiq);
}

vec3 hash33(vec3 p3) {
  p3 = fract(p3 * vec3(0.1031, 0.11369, 0.13787));
  p3 += dot(p3, p3.yxz + 19.19);
  return -1.0 + 2.0 * fract(vec3(
    p3.x + p3.y,
    p3.x + p3.z,
    p3.y + p3.z
  ) * p3.zyx);
}

float snoise3(vec3 p) {
  const float K1 = 0.333333333;
  const float K2 = 0.166666667;
  vec3 i = floor(p + (p.x + p.y + p.z) * K1);
  vec3 d0 = p - (i - (i.x + i.y + i.z) * K2);
  vec3 e = step(vec3(0.0), d0 - d0.yzx);
  vec3 i1 = e * (1.0 - e.zxy);
  vec3 i2 = 1.0 - e.zxy * (1.0 - e);
  vec3 d1 = d0 - (i1 - K2);
  vec3 d2 = d0 - (i2 - K1);
  vec3 d3 = d0 - 0.5;
  vec4 h = max(0.6 - vec4(
    dot(d0, d0),
    dot(d1, d1),
    dot(d2, d2),
    dot(d3, d3)
  ), 0.0);
  vec4 n = h * h * h * h * vec4(
    dot(d0, hash33(i)),
    dot(d1, hash33(i + i1)),
    dot(d2, hash33(i + i2)),
    dot(d3, hash33(i + 1.0))
  );
  return dot(vec4(31.316), n);
}

vec4 extractAlpha(vec3 colorIn) {
  float a = max(max(colorIn.r, colorIn.g), colorIn.b);
  return vec4(colorIn.rgb / (a + 1e-5), a);
}

const baseColor1 = vec3(0.95, 0.98, 1.0);   // Frosted White
const baseColor2 = vec3(0.50, 0.80, 1.0);   // Ice Blue
const baseColor3 = vec3(0.15, 0.35, 0.85);  // Deep Azure
const float innerRadius = 0.6;
const float noiseScale = 0.65;

float light1(float intensity, float attenuation, float dist) {
  return intensity / (1.0 + dist * attenuation);
}

float light2(float intensity, float attenuation, float dist) {
  return intensity / (1.0 + dist * dist * attenuation);
}

vec4 draw(vec2 uv) {
  vec3 color1 = adjustHue(baseColor1, hue);
  vec3 color2 = adjustHue(baseColor2, hue);
  vec3 color3 = adjustHue(baseColor3, hue);

  float ang = atan(uv.y, uv.x);
  float len = length(uv);
  float invLen = len > 0.0 ? 1.0 / len : 0.0;

  float n0 = snoise3(vec3(uv * noiseScale, iTime * 0.5)) * 0.5 + 0.5;
  float r0 = mix(mix(innerRadius, 1.0, 0.4), mix(innerRadius, 1.0, 0.6), n0);
  float d0 = distance(uv, (r0 * invLen) * uv);
  float v0 = light1(1.0, 10.0, d0);
  v0 *= smoothstep(r0 * 1.05, r0, len);
  float cl = cos(ang + iTime * 2.0) * 0.5 + 0.5;

  float a = iTime * -1.0;
  vec2 pos = vec2(cos(a), sin(a)) * r0;
  float d = distance(uv, pos);
  float v1 = light2(1.5, 5.0, d);
  v1 *= light1(1.0, 50.0, d0);

  float v2 = smoothstep(1.0, mix(innerRadius, 1.0, n0 * 0.5), len);
  float v3 = smoothstep(innerRadius, mix(innerRadius, 1.0, 0.5), len);

  vec3 col = mix(color1, color2, cl);
  col = mix(color3, col, v0);
  col = (col + v1) * v2 * v3;
  col = clamp(col, 0.0, 1.0);

  return extractAlpha(col);
}

// The orb's outer edge sits at a radius of one, which is exactly the edge of
// the viewport -- and the noise that gives it its organic shape pushes past
// that, so the reference clips flat against all four sides. Scaling the
// coordinates out leaves room for the wobble and the glow.
const float FIT = 1.35;

vec4 mainImage(vec2 fragCoord) {
  vec2 center = iResolution.xy * 0.5;
  float size = min(iResolution.x, iResolution.y);
  vec2 uv = (fragCoord - center) / size * 2.0 * FIT;

  float angle = rot;
  float s = sin(angle);
  float c = cos(angle);
  uv = vec2(c * uv.x - s * uv.y, s * uv.x + c * uv.y);

  // Audio Visualizer effect: intense wobble when hover (energy) is high
  float energyWobble = 1.0 + (hover * hoverIntensity * 15.0);
  uv.x += hover * hoverIntensity * 0.15 * sin(uv.y * 10.0 * energyWobble + iTime * energyWobble);
  uv.y += hover * hoverIntensity * 0.15 * sin(uv.x * 10.0 * energyWobble + iTime * energyWobble);

  // High-frequency ripple
  uv += hover * hoverIntensity * 0.05 * vec2(sin(iTime * 20.0), cos(iTime * 20.0));

  return draw(uv);
}

void main() {
  vec2 fragCoord = vUv * iResolution.xy;
  vec4 col = mainImage(fragCoord);
  gl_FragColor = vec4(col.rgb * col.a, col.a * opacity);
}
`;

// Minimalist Hues: Base is Ice Blue
const STATE_HUE = {
  idle: 0,         // Ice Blue
  listening: 15,   // Slightly cooler
  thinking: 30,    // Azure
  speaking: 0,     // Ice Blue
};

// Idle fades out rather than sitting on top of everything doing nothing.
const STATE_OPACITY = {
  idle: 0.0,
  listening: 1.0,
  thinking: 1.0,
  speaking: 1.0,
};

// How quickly displayed values chase their targets, per frame at 60fps.
// Low enough that a burst of volume reads as a swell rather than a flicker.
const EASE = 0.12;
const OPACITY_EASE = 0.08;

const BASE_ROTATION = 0.5;
const MAX_ROTATION = 4.0; // Faster spin
const MAX_HOVER_INTENSITY = 1.5; // Bigger ripples


function compile(gl, type, source) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    throw new Error(gl.getShaderInfoLog(shader) || 'shader failed to compile');
  }
  return shader;
}


function createProgram(gl) {
  const program = gl.createProgram();
  gl.attachShader(program, compile(gl, gl.VERTEX_SHADER, VERTEX_SHADER));
  gl.attachShader(program, compile(gl, gl.FRAGMENT_SHADER, FRAGMENT_SHADER));
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    throw new Error(gl.getProgramInfoLog(program) || 'program failed to link');
  }
  return program;
}


class Orb {
  constructor(canvas) {
    this.canvas = canvas;
    // premultipliedAlpha matches what the shader outputs, and a transparent
    // clear colour is what lets the window behind show through.
    this.gl = canvas.getContext('webgl', {
      alpha: true,
      premultipliedAlpha: true,
      antialias: true,
    });
    if (!this.gl) {
      throw new Error('WebGL is unavailable');
    }

    const gl = this.gl;
    gl.clearColor(0, 0, 0, 0);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);

    this.program = createProgram(gl);
    gl.useProgram(this.program);

    // One triangle large enough to cover the viewport. Cheaper than two, and
    // avoids the seam a quad's diagonal can show in a fragment shader.
    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
      -1, -1, 0, 0,
       3, -1, 2, 0,
      -1,  3, 0, 2,
    ]), gl.STATIC_DRAW);

    const stride = 4 * 4;
    const position = gl.getAttribLocation(this.program, 'position');
    gl.enableVertexAttribArray(position);
    gl.vertexAttribPointer(position, 2, gl.FLOAT, false, stride, 0);

    const uv = gl.getAttribLocation(this.program, 'uv');
    gl.enableVertexAttribArray(uv);
    gl.vertexAttribPointer(uv, 2, gl.FLOAT, false, stride, 2 * 4);

    this.uniforms = {};
    for (const name of ['iTime', 'iResolution', 'hue', 'hover', 'rot',
                        'hoverIntensity', 'opacity']) {
      this.uniforms[name] = gl.getUniformLocation(this.program, name);
    }

    // What the application last told us.
    this.target = { state: 'idle', input: 0, output: 0 };
    // What is actually being drawn, always chasing the target.
    this.shown = { hue: 0, input: 0, output: 0, opacity: 0 };

    this.rotation = 0;
    this.lastFrame = 0;

    window.addEventListener('resize', () => this.resize());
    this.resize();
  }

  /** Accept a state update from the application. */
  update(message) {
    if (typeof message.state === 'string' && message.state in STATE_HUE) {
      this.target.state = message.state;
    }
    if (typeof message.input === 'number') {
      this.target.input = Math.min(1, Math.max(0, message.input));
    }
    if (typeof message.output === 'number') {
      this.target.output = Math.min(1, Math.max(0, message.output));
    }
  }

  resize() {
    // Measured from the window rather than the element. A canvas reports its
    // layout size, which is not always the size actually being painted -- and
    // when the two disagree the shader centres the orb on the wrong point,
    // leaving it sitting off to one side for no visible reason.
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const width = Math.max(1, Math.round(window.innerWidth * dpr));
    const height = Math.max(1, Math.round(window.innerHeight * dpr));

    if (this.canvas.width === width && this.canvas.height === height) {
      return;
    }
    this.canvas.width = width;
    this.canvas.height = height;
    this.canvas.style.width = window.innerWidth + 'px';
    this.canvas.style.height = window.innerHeight + 'px';
    this.gl.viewport(0, 0, this.gl.drawingBufferWidth, this.gl.drawingBufferHeight);
  }

  frame(now) {
    const gl = this.gl;
    const delta = this.lastFrame ? (now - this.lastFrame) * 0.001 : 0;
    this.lastFrame = now;

    const hue = STATE_HUE[this.target.state];
    const opacity = STATE_OPACITY[this.target.state];

    this.shown.hue += (hue - this.shown.hue) * EASE;
    this.shown.input += (this.target.input - this.shown.input) * EASE;
    this.shown.output += (this.target.output - this.shown.output) * EASE;
    this.shown.opacity += (opacity - this.shown.opacity) * OPACITY_EASE;

    // Both directions move it. Only the user's voice does in the original,
    // which leaves the orb sitting still while Bruno talks -- and a companion
    // that freezes the moment it answers looks broken rather than calm.
    const energy = Math.max(this.shown.input, this.shown.output);
    this.rotation += delta * (BASE_ROTATION + energy * MAX_ROTATION);

    // Taken from the drawing buffer, which is what the shader is actually
    // painting into. The canvas attributes can disagree with it.
    const width = gl.drawingBufferWidth;
    const height = gl.drawingBufferHeight;

    gl.uniform1f(this.uniforms.iTime, now * 0.001);
    gl.uniform3f(this.uniforms.iResolution, width, height, width / height);
    gl.uniform1f(this.uniforms.hue, this.shown.hue);
    gl.uniform1f(this.uniforms.hover, Math.min(energy * 2.0, 1.0));
    gl.uniform1f(this.uniforms.rot, this.rotation);
    gl.uniform1f(this.uniforms.hoverIntensity,
                 Math.min(energy * MAX_HOVER_INTENSITY, MAX_HOVER_INTENSITY));
    gl.uniform1f(this.uniforms.opacity, this.shown.opacity);

    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }

  start() {
    const loop = (now) => {
      this.frame(now);
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }
}


// -- wiring ----------------------------------------------------------------

const orb = new Orb(document.getElementById('orb'));
orb.start();

// The application calls this. Exposed on window so a host that can only
// evaluate a string of JavaScript still has a way in.
window.brunoUpdate = (message) => orb.update(message);

const query = new URLSearchParams(location.search);

// Pin a single state and level, for looking at one appearance rather than a
// cycle. Tuning colour against a moving target is guesswork.
if (query.has('state')) {
  const held = {
    state: query.get('state'),
    input: parseFloat(query.get('input') || '0'),
    output: parseFloat(query.get('output') || '0'),
  };
  orb.update(held);
  // Skip the fade so a still frame shows the orb at full strength.
  orb.shown.opacity = STATE_OPACITY[held.state] ?? 1;
  orb.shown.hue = STATE_HUE[held.state] ?? 0;
  orb.shown.input = held.input;
  orb.shown.output = held.output;
}

// Standing in for Bruno, so the page can be opened in a browser and judged
// without running anything else.
if (query.has('demo')) {
  const script = [
    { state: 'idle', hold: 1500 },
    { state: 'listening', hold: 3000 },
    { state: 'thinking', hold: 2000 },
    { state: 'speaking', hold: 4000 },
  ];
  let step = 0;
  const advance = () => {
    const { state, hold } = script[step % script.length];
    orb.update({ state });
    step += 1;
    setTimeout(advance, hold);
  };
  advance();

  // Rough stand-in for speech: a wandering level rather than a clean sine, so
  // the motion is judged against something like real input.
  setInterval(() => {
    const t = performance.now() * 0.001;
    const speaking = orb.target.state === 'speaking';
    const listening = orb.target.state === 'listening';
    const wobble = 0.5 + 0.4 * Math.sin(t * 5.0) * Math.sin(t * 1.7 + 0.4);
    orb.update({
      input: listening ? Math.max(0, wobble) : 0,
      output: speaking ? Math.max(0, wobble) : 0,
    });
  }, 50);
}
