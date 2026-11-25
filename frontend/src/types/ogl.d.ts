declare module 'ogl' {
  export interface RendererOptions {
    dpr?: number;
    alpha?: boolean;
    antialias?: boolean;
    depth?: boolean;
    stencil?: boolean;
    premultipliedAlpha?: boolean;
    preserveDrawingBuffer?: boolean;
    powerPreference?: string;
    autoClear?: boolean;
    webgl?: number;
    width?: number;
    height?: number;
    [key: string]: unknown;
  }

  export class Renderer {
    constructor(options?: RendererOptions);
    gl: WebGLRenderingContext & {
      canvas: HTMLCanvasElement;
      drawingBufferWidth: number;
      drawingBufferHeight: number;
    };
    dpr: number;
    width: number;
    height: number;
    setSize(width: number, height: number): void;
    render(options: { scene: Mesh | Transform; camera?: unknown }): void;
    destroy(): void;
  }

  export interface ProgramOptions {
    vertex: string;
    fragment: string;
    uniforms?: Record<string, { value: unknown }>;
    transparent?: boolean;
    cullFace?: boolean;
    frontFace?: number;
    depthTest?: boolean;
    depthWrite?: boolean;
    depthFunc?: number;
    [key: string]: unknown;
  }

  export class Program {
    constructor(gl: unknown, options: ProgramOptions);
    uniforms: Record<string, { value: unknown }>;
    remove(): void;
  }

  export class Geometry {
    constructor(gl: unknown, attributes?: Record<string, unknown>);
    remove(): void;
  }

  export class Triangle extends Geometry {
    constructor(gl: unknown);
    remove(): void;
  }

  export class Transform {
    addChild(child: Transform): void;
    removeChild(child: Transform): void;
  }

  export interface MeshOptions {
    geometry: Geometry;
    program: Program;
    mode?: number;
    frustumCulled?: boolean;
    renderOrder?: number;
  }

  export class Mesh extends Transform {
    constructor(gl: unknown, options: MeshOptions);
    geometry: Geometry;
    program: Program;
    remove(): void;
  }
}
