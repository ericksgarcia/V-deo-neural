"""blender_walk.py: monta o personagem de perfil no Blender (malha densa + pesos + armadura com IK) e renderiza a caminhada (Cycles, CPU).
uso: bpyenv/bin/python poc3/blender_walk.py <saida_dir> [frames] [frame_inicial]
Saída: PNGs RGBA (personagem olhando para a ESQUERDA, andando para a esquerda; inverter na horizontal no vídeo)."""
import bpy,sys,os,json,math
from mathutils import Vector,Quaternion
sys.path.insert(0,'poc3');import walkspec as W
OUT=sys.argv[1];NF=int(sys.argv[2]) if len(sys.argv)>2 else 96;F0=int(sys.argv[3]) if len(sys.argv)>3 else 0
FPS=24;S=0.001;OX,OZ=1030,2030;PXM=0.29                       # vb->m ; px de tela por vb
def P(x,y): return Vector(((x-OX)*S,0,(OZ-y)*S))
bpy.ops.wm.read_factory_settings(use_empty=True);sc=bpy.context.scene
sc.render.fps=FPS

# ---------- armadura ----------
arm=bpy.data.armatures.new('rig');ao=bpy.data.objects.new('rig',arm);sc.collection.objects.link(ao)
bpy.context.view_layer.objects.active=ao;bpy.ops.object.mode_set(mode='EDIT')
BONES={ # nome:(cabeça,cauda,pai)
 'root':(P(1030,2030),P(1030,1990),None),'pelvis':(P(1060,1090),P(1055,800),'root'),'skirt':(P(1060,1100),P(1060,1830),'pelvis'),
 'chest':(P(1055,800),P(1010,470),'pelvis'),'neck':(P(1010,470),P(1010,440),'chest'),'head':(P(1010,470),P(1010,110),'neck'),
 'sho':(P(1130,540),P(1115,830),'chest'),'elb':(P(1115,830),P(1105,950),'sho'),'fore1':(P(1105,950),P(1090,1100),'elb'),'hand':(P(1090,1100),P(1075,1370),'fore1'),
 'thigh.F':(P(1040,1100),P(1010,1500),'pelvis'),'shin.F':(P(1010,1500),P(1030,1925),'thigh.F'),'foot.F':(P(1030,1925),P(840,2010),'shin.F'),
 'thigh.B':(P(1090,1100),P(1070,1500),'pelvis'),'shin.B':(P(1070,1500),P(1130,1925),'thigh.B'),'foot.B':(P(1130,1925),P(960,2010),'shin.B'),
 'ik.F':(P(1030,1925),P(840,2010),'root'),'ik.B':(P(1130,1925),P(960,2010),'root')}
for n,(h,t,p) in BONES.items():
    b=arm.edit_bones.new(n);b.head=h;b.tail=t
    if p:b.parent=arm.edit_bones[p]
bpy.ops.object.mode_set(mode='OBJECT')

# ---------- malhas ----------
LAYERS=['legB','footB','legF','footF','body','arm']
ske=json.load(open('poc2/out/jesus_side_ske.json'))['armature'][0];bnames=[b['name'] for b in ske['bone']]
OLD2NEW={'ankF':'foot.F','ankB':'foot.B'}
objs=[]
for li,L in enumerate(LAYERS):
    d=[s for s in ske['skin'][0]['slot'] if s['name']==L][0]['display'][0]
    V=d['vertices'];UV=d['uvs'];T=d['triangles'];Wt=d['weights'];n=len(V)//2
    verts=[tuple(P(V[2*i],V[2*i+1])+Vector((0,(len(LAYERS)-li)*0.0004,0))) for i in range(n)]
    me=bpy.data.meshes.new(L);me.from_pydata(verts,[],[tuple(T[3*i:3*i+3]) for i in range(len(T)//3)]);me.update()
    uv=me.uv_layers.new(name='uv')
    for loop in me.loops: uv.data[loop.index].uv=(UV[2*loop.vertex_index],1.0-UV[2*loop.vertex_index+1])
    ob=bpy.data.objects.new(L,me);sc.collection.objects.link(ob);objs.append(ob)
    # pesos
    vgs={}
    def vg(name):
        if name not in vgs:vgs[name]=ob.vertex_groups.new(name=name)
        return vgs[name]
    if L in('footB','footF'):
        for i in range(n): vg('foot.F' if L=='footF' else 'foot.B').add([i],1.0,'REPLACE')
    elif L in('legB','legF'):
        side='B' if L=='legB' else 'F'
        for i in range(n):
            y=V[2*i+1];w=min(1,max(0,(y-1850)/70.0))            # canela (tubo) -> pé
            vg('shin.'+side).add([i],1-w,'REPLACE')
            if w>0:vg('foot.'+side).add([i],w,'REPLACE')
    else:
        k=0
        for i in range(n):
            c=Wt[k];k+=1
            for _ in range(c):
                bi=Wt[k];w=Wt[k+1];k+=2;nm=OLD2NEW.get(bnames[bi],bnames[bi]);vg(nm).add([i],w,'REPLACE')
    m=ob.modifiers.new('arm','ARMATURE');m.object=ao
    # material (emissivo + alfa)
    mat=bpy.data.materials.new(L);mat.use_nodes=True;nt=mat.node_tree;nt.nodes.clear()
    img=bpy.data.images.load(os.path.abspath(f'poc2/out/jesus_side_{L}.png'));img.alpha_mode='STRAIGHT'
    tx=nt.nodes.new('ShaderNodeTexImage');tx.image=img;tx.interpolation='Linear';tx.extension='CLIP'
    em=nt.nodes.new('ShaderNodeEmission');tr=nt.nodes.new('ShaderNodeBsdfTransparent');mx=nt.nodes.new('ShaderNodeMixShader');ou=nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(tx.outputs['Color'],em.inputs['Color']);nt.links.new(tx.outputs['Alpha'],mx.inputs['Fac'])
    nt.links.new(tr.outputs[0],mx.inputs[1]);nt.links.new(em.outputs[0],mx.inputs[2]);nt.links.new(mx.outputs[0],ou.inputs[0])
    ob.data.materials.append(mat)

# ---------- IK ----------
bpy.context.view_layer.objects.active=ao;bpy.ops.object.mode_set(mode='POSE')
def axis_local(pb):
    a=pb.bone.matrix_local.to_3x3().inverted()@Vector((0,1,0));return a.normalized()
for s in 'FB':
    sh=ao.pose.bones['shin.'+s];c=sh.constraints.new('IK');c.target=ao;c.subtarget='ik.'+s;c.chain_count=2;c.use_tail=True
    a=axis_local(sh);keep=max(range(3),key=lambda i:abs(a[i]))
    for pb in (sh,ao.pose.bones['thigh.'+s]):
        pb.lock_ik_x=(keep!=0);pb.lock_ik_y=True;pb.lock_ik_z=(keep!=2)
    ft=ao.pose.bones['foot.'+s];cr=ft.constraints.new('COPY_ROTATION');cr.target=ao;cr.subtarget='ik.'+s;cr.target_space='WORLD';cr.owner_space='WORLD'
for pb in ao.pose.bones: pb.rotation_mode='QUATERNION'

def rot_y(pb,deg): pb.rotation_quaternion=Quaternion(axis_local(pb),math.radians(deg))
def loc_w(pb,v): pb.location=pb.bone.matrix_local.to_3x3().inverted()@v
# ---------- animação (quadro a quadro, curvas bezier automáticas) ----------
total=NF
for f in range(total):
    fr=F0+f;t=fr/FPS;phi=(t/W.T)%1.0;B=W.body(phi);pb=ao.pose.bones
    xs=(640-150-W.V_VB*PXM*t)*0.003448   # px de tela (espelhado depois) -> m
    loc_w(pb['root'],Vector((xs,0,0)));
    loc_w(pb['pelvis'],Vector((0,0,B['pelvis_up']*S)))
    for n,k in (('chest','chest'),('neck','neck'),('head','head'),('sho','sho'),('elb','elb'),('fore1','fore1'),('hand','hand'),('skirt','skirt')): rot_y(pb[n],B[k])
    for s,off in (('F',0.0),('B',0.5)):
        dx,up,pitch=W.foot(phi+off);loc_w(pb['ik.'+s],Vector((dx*S,0,up*S)));rot_y(pb['ik.'+s],pitch)
    for pbn in pb:
        pbn.keyframe_insert('location',frame=f+1);pbn.keyframe_insert('rotation_quaternion',frame=f+1)
bpy.ops.object.mode_set(mode='OBJECT')

# ---------- câmera / render ----------
cam=bpy.data.cameras.new('c');cam.type='ORTHO';cam.ortho_scale=1280*0.003448;co=bpy.data.objects.new('c',cam);sc.collection.objects.link(co)
co.location=(0,-5,(662-360)*0.003448);co.rotation_euler=(math.radians(90),0,0);sc.camera=co
r=sc.render;r.engine='CYCLES';r.resolution_x=1280;r.resolution_y=720;r.film_transparent=True;r.image_settings.file_format='PNG';r.image_settings.color_mode='RGBA'
sc.cycles.device='CPU';sc.cycles.samples=int(os.environ.get('SAMPLES','8'));sc.cycles.use_denoising=False;sc.cycles.filter_width=1.2
sc.view_settings.view_transform='Standard';sc.view_settings.look='None';sc.display_settings.display_device='sRGB'
sc.cycles.max_bounces=2;sc.cycles.transparent_max_bounces=24
os.makedirs(OUT,exist_ok=True)
import time
for f in range(total):
    sc.frame_set(f+1);r.filepath=f'{OUT}/f{f:04d}.png';t0=time.time();bpy.ops.render.render(write_still=True);print('frame',f,round(time.time()-t0,1),'s',flush=True)
