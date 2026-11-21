import bpy, math, os, bmesh
from mathutils import Vector
from math import sin, cos, pi
b=bpy
b.ops.wm.read_factory_settings(use_empty=True)
sc=b.context.scene
sc.unit_settings.system='METRIC'
sc.unit_settings.scale_length=.001
red=(.48,.035,.024); blue=(.032,.17,.22); skin=(.84,.42,.23); pink=(.73,.25,.14); ivory=(.86,.77,.59); boot=(.12,.055,.032); dark=(.065,.024,.018); green=(.12,.21,.12)
def finish(o,name,c):
 o.name=name;o.color=(*c,1)
 key=str(c)
 m=b.data.materials.get(key) or b.data.materials.new(key);m.diffuse_color=(*c,1);o.data.materials.append(m)
 for p in o.data.polygons:p.use_smooth=True
 return o
def bulb(name,pos,size,c,tilt=0):
 b.ops.mesh.primitive_uv_sphere_add(segments=40,ring_count=24,location=pos);o=b.context.object;o.scale=size;o.rotation_euler.y=tilt
 return finish(o,name,c)
def loft(name,rings,c):
 vs=[];fs=[];n=56
 for x,y,z,a,d in rings:
  for i in range(n):
   t=i*2*pi/n;vs.append((x+a*cos(t),y+d*sin(t),z))
 for j in range(len(rings)-1):
  for i in range(n):
   k=j*n+i;l=j*n+(i+1)%n;fs.append((k,l,l+n,k+n))
 fs.extend([tuple(reversed(range(n))),tuple(range(len(vs)-n,len(vs)))])
 mesh=b.data.meshes.new(name);mesh.from_pydata(vs,[],fs);mesh.update();o=b.data.objects.new(name,mesh);sc.collection.objects.link(o)
 mod=o.modifiers.new('Soft contours','SUBSURF');mod.levels=2
 return finish(o,name,c)
def line(name,pts,r,c):
 cu=b.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.bevel_depth=r;cu.bevel_resolution=4;cu.resolution_u=12;cu.use_fill_caps=True
 sp=cu.splines.new('BEZIER');sp.bezier_points.add(len(pts)-1)
 for p,v in zip(sp.bezier_points,pts):
  p.co=v[:3];p.handle_left_type=p.handle_right_type='AUTO';p.radius=v[3] if len(v)>3 else 1
 o=b.data.objects.new(name,cu);sc.collection.objects.link(o);o.color=(*c,1);o.data.materials.append(b.data.materials[str(c)])
loft('Oval shelf plinth',[(0,0,0,25,18),(0,0,0,27,20),(0,0,1,28,21),(0,0,3,28,21),(0,0,4,26,19)],green)
for t in [-1,1]:
 bulb('Leather shoe',(t*11,-4,8),(10,14,6),boot)
 bulb('Stocking',(t*10,1,18),(7,8,13),skin)
 for i in range(3):bulb('Bunched trouser fold',(t*10,1,12+i*2.1),(8.5+i*.25,9,2.6),blue,t*.08)
 bulb('Haunch',(t*7.5,7,30),(10,11,12),skin)
bulb('Hiked tunic',(0,-1,40),(20,15,15),blue)
bulb('Low front breeches',(0,-5,28),(17,10,8),blue)
for t in [-1,1]:
 bulb('Bent sleeve',(t*16,-1,44),(7,8,11),blue,-t*.34)
 bulb('Elbow',(t*20,1,39),(5,6,6),blue)
 bulb('Hand at hip',(t*18,5,36),(4.7,6,5),skin)
 for i in range(4):bulb('Finger',(t*(16+i*1.35),8,34.4+i*.35),(1.35,2.3,3.1),skin,t*.16)
 bulb('Thumb',(t*20,1.7,36),(2.2,3,3),skin)
bulb('Head',(0,-4,61),(18,15,17),skin)
for t in [-1,1]:
 bulb('Ear',(t*17,-4,62),(4.5,3.4,6),skin,t*.3)
 bulb('Inner ear',(t*18,-6.4,62),(2.4,1.5,3.4),pink,t*.3)
bulb('Beard mantle',(0,-12,51),(16,9,12),ivory)
for i in range(-4,5):
 x=i*3.3;z=34+abs(i)*2.1;y=-18+abs(i)*.8
 loft('Carved beard lock',[(x-1,y-1,z,.35,.35),(x-1,y-1,z+2,1.7,1.6),(x+1,y,z+6,3.5,3.4),(x,y,z+12,4.7,4),(x*.91,y+1,55,3.8,3.5)],ivory)
for t in [-1,1]:bulb('Smile cheek',(t*10,-15.7,60),(6,4,4.6),skin,t*.22)
bulb('Grinning mouth',(0,-20.1,54),(7,2.1,3.6),dark,-.11)
bulb('Tongue',(1,-21.7,52.8),(3.3,.9,1.2),pink,-.08)
for t in [-1,1]:
 line('Swept moustache',[(t*1,-20.7,58,.65),(t*4,-21.4,57.4,1.15),(t*8,-20.1,56.5,.85),(t*12,-18.5,58.5,.12)],2.6,ivory)
bulb('Open eye',(-6.4,-17.6,65),(3.9,2.7,4.4),ivory)
bulb('Pupil',(-5.9,-19.8,65),(1.9,1.05,2.5),dark)
bulb('Catchlight',(-6.4,-20.6,66),(.65,.46,.68),ivory)
line('Winking eyelid',[(2.7,-18.5,64,.3),(6.2,-18.9,65,1),(10.4,-17,64.4,.22)],1.15,dark)
for t in [-1,1]:line('Expressive eyebrow',[(t*2,-17,68.5,.42),(t*6,-17.5,69.8+(t<0),1),(t*11,-15,68.6,.25)],2.3,ivory)
bulb('Bulbous nose',(0,-20.2,61.7),(6.1,5.4,4.8),skin)
loft('Slouched cap',[(0,-3,70,16,14),(0,-3,70.5,19,16),(0,-2,73,19.6,16.5),(-1,-1,76,18.5,15.7),(-2,0,79,15.8,14),(-3,0,81,17,14),(-3,1,83,16.6,13),(-3,1,86,13,11),(-2,1,92,11,9),(2,1,98,8.4,7),(8,1,102,6.3,5),(14,1,103,4.6,3.5),(18,1,101,3,2.4),(20,1,98,1.4,1.2),(20.8,1,97,.3,.3)],red)
def camera(pos,target):
 b.ops.object.camera_add(location=pos);cam=b.context.object;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=122;cam.data.clip_end=1000;sc.camera=cam;return cam
cam=camera((95,-205,99),(0,0,52))
sc.render.engine='BLENDER_WORKBENCH'
sh=sc.display.shading;sh.light='STUDIO';sh.color_type='OBJECT';sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='WORLD';sh.show_specular_highlight=True
sc.render.resolution_x=620;sc.render.resolution_y=680;sc.render.resolution_percentage=100
for a in b.context.screen.areas:
 if a.type=='VIEW_3D':
  a.spaces.active.region_3d.view_perspective='CAMERA';a.spaces.active.shading.color_type='OBJECT';a.spaces.active.overlay.show_overlays=False
b.ops.object.select_all(action='DESELECT')
b.ops.wm.save_as_mainfile(filepath=os.path.abspath('Clive.blend'))
for n,pos in [('Front',(83,-220,92)),('Rear',(98,210,90))]:
 cam.location=pos;cam.rotation_euler=(Vector((0,0,52))-cam.location).to_track_quat('-Z','Y').to_euler()
 sc.render.filepath=os.path.abspath(n+'.png');b.ops.render.render(write_still=True)
for o in sc.objects:o.select_set(o.type in {'MESH','CURVE'})
b.context.view_layer.objects.active=next(o for o in sc.objects if o.type=='MESH')
b.ops.object.convert(target='MESH');b.ops.object.join();o=b.context.object;b.ops.object.transform_apply(location=True,rotation=True,scale=True)
o.data.remesh_voxel_size=.32;b.ops.object.voxel_remesh()
bm=bmesh.new();bm.from_mesh(o.data);print('nonmanifold edges',sum(not e.is_manifold for e in bm.edges));bm.free()
b.ops.wm.stl_export(filepath=os.path.abspath('Clive.stl'),export_selected_objects=True)