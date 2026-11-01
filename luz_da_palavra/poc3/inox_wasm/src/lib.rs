//! Player mínimo do Inox2D para WebAssembly: carrega .inp, recebe parâmetros e desenha quadros determinísticos.
use glam::Vec2;
use inox2d::formats::inp::parse_inp;
use inox2d::puppet::Puppet;
use inox2d::render::InoxRendererExt;
use inox2d_opengl::OpenglRenderer;
use wasm_bindgen::prelude::*;
use wasm_bindgen::JsCast;

#[wasm_bindgen]
pub struct Player {
    renderer: OpenglRenderer,
    puppet: Puppet,
}

#[wasm_bindgen]
impl Player {
    #[wasm_bindgen(constructor)]
    pub fn new(canvas_id: &str, inp: &[u8], scale: f32) -> Result<Player, JsValue> {
        console_error_panic_hook::set_once();
        let doc = web_sys::window().unwrap().document().unwrap();
        let canvas = doc.get_element_by_id(canvas_id).unwrap().dyn_into::<web_sys::HtmlCanvasElement>()?;
        let opts = js_sys::Object::new();
        js_sys::Reflect::set(&opts, &"stencil".into(), &true.into())?;
        js_sys::Reflect::set(&opts, &"alpha".into(), &true.into())?;
        js_sys::Reflect::set(&opts, &"premultipliedAlpha".into(), &true.into())?;
        js_sys::Reflect::set(&opts, &"preserveDrawingBuffer".into(), &true.into())?;
        js_sys::Reflect::set(&opts, &"antialias".into(), &true.into())?;
        let ctx = canvas
            .get_context_with_context_options("webgl2", &opts)?
            .unwrap()
            .dyn_into::<web_sys::WebGl2RenderingContext>()?;
        let gl = glow::Context::from_webgl2_context(ctx);
        let mut model = parse_inp(inp).map_err(|e| JsValue::from_str(&format!("{e}")))?;
        model.puppet.init_transforms();
        model.puppet.init_rendering();
        model.puppet.init_params();
        model.puppet.init_physics();
        let mut renderer = OpenglRenderer::new(gl, &model).map_err(|e| JsValue::from_str(&format!("{e:?}")))?;
        renderer.resize(canvas.width(), canvas.height());
        renderer.camera.scale = Vec2::splat(scale);
        Ok(Player { renderer, puppet: model.puppet })
    }
    pub fn set_camera(&mut self, x: f32, y: f32, scale: f32) {
        self.renderer.camera.position = Vec2::new(x, y);
        self.renderer.camera.scale = Vec2::splat(scale);
    }
    pub fn begin(&mut self) {
        self.renderer.clear();
        self.puppet.begin_frame();
    }
    pub fn set_param(&mut self, name: &str, x: f32, y: f32) -> Result<(), JsValue> {
        self.puppet
            .param_ctx
            .as_mut()
            .unwrap()
            .set(name, Vec2::new(x, y))
            .map_err(|e| JsValue::from_str(&format!("{e:?}")))
    }
    pub fn end_and_draw(&mut self, dt: f32) {
        self.puppet.end_frame(dt);
        self.renderer.on_begin_draw(&self.puppet);
        self.renderer.draw(&self.puppet);
        self.renderer.on_end_draw(&self.puppet);
    }
}
