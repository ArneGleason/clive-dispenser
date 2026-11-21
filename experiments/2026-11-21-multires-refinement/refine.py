import bpy, bmesh, math, sys
from math import sin, cos, exp, pi, atan2
from pathlib import Path
from mathutils import Vector
out=Path(__file__).resolve().parent
source=Path(sys.argv[-1]) if '--' in sys.argv else out.parent/'subd-study'/'Clive-SubD.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
sc=bpy.context.scene
def ga(v,center,width): return exp(-((v-center)/width)**2)
def clamp(x):return max(0,min(1,x))
def cheek(x,z):return ga(x,9,6)*ga(z,69.4,5)
hair=('Beard','Arched brow','Upswept','Temple curl','Nape curl')
def coarse(n,x,y,z):
 sign=1 if x>0 else -1
 if n.startswith(('Face','Tooth','Upswept','Arched brow')):
  front=clamp((-y-12)/8);c=cheek(x,z)*front
  rise=2.2*ga(x,8,5.8)*ga(z,65,5)*front
  z+=1.2*c+rise;y-=2.1*c
  if n.startswith('Face'):
   nose=clamp((-y-25)/6)*ga(x,0,6)*ga(z,69.5,4)
   x*=1+.23*nose;z+=(z-70)*.22*nose;y+=1.5*nose
   # Knit eyelids inward; leave the open eye looking toward the grin.
   w=ga(x,7.6,3.8)*ga(z,74.7,1.7)*front;z+=(74.7-z)*.62*w
   x+=.7*ga(x,-6.5,2)*ga(z,74,1.8)*front
  if n.startswith('Arched brow'):z+=.9*ga(abs(x),6,4);y-=.5
 if n.startswith('Beard'):
  x+=2.2*sin((z-42)*.38+x*.10)*clamp((66-z)/8)
  y-=1.25*sin((z-41)*.32+x*.12)*clamp((64-z)/9)
 if n.startswith('Nape curl'):x+=1.65*sin(.35*z+.16*x);z+=1.15*cos(x*.42)
 if n.startswith('Cap'):
  t=atan2((y+12)/14,x/17);z+=1.9*cos(2*t+(z-81)*.18)*ga(z,85,8)+1.5*cos(t+.6)*ga(z,79,6)
 if n.startswith('Seat'):
  x=(x-sign*8.6)*1.06+sign*8.1;y+=1.8*ga(z,42,8);z-=1.2*ga(z,37,6)
 if n.startswith('Smock'):
  z+=1.5*cos(x*.14+.6)*clamp((y-1)/15)*ga(z,54,7)
 if n.startswith(('Forearm','Curled finger','Thumb')):
  c=ga(z,35.7,4.5);x+=(x-sign*10)*.20*c;y-=1.0*c;z+=(z-35.5)*.19*c
 if n.startswith('Boot'):y-=2.5*clamp((-y+1)/11)*ga(z,15,4)
 return x,y,z
objs=[o for o in sc.objects if o.type=='MESH']
for o in objs:
 for v in o.data.vertices:v.co=coarse(o.name,*v.co)
# Corrections from the high front, low side and rear three-quarter inspections.
def round_forms(o):
 n=o.name
 for v in o.data.vertices:
  x,y,z=v.co;h=1 if x>=0 else -1
  if n.startswith('Smock'):
   # Bring the collar forward into the nape and round out the shoulder blades.
   z+=3.3*ga(y,0,15)*ga(z,66,6);y-=3.1*ga(z,67,6)
   x*=1+.07*ga(z,60,8);z+=1.8*ga(y,16,12)*ga(z,61,8)
  if n.startswith('Sleeve'):
   x+=h*.85*ga(z,57,8);y-=1.2*ga(z,62,5)
  if n.startswith('Seat'):
   y-=3.5*clamp((y-10)/16)*ga(z,42,10)
   z+=1.0*ga(y,23,8)*ga(z,35,5)
   x-=h*.7*ga(y,21,8)*ga(z,50,6)
  if n.startswith(('Waistband','Front trouser panel')):
   y-=5.5*clamp((-y+3)/12)*ga(z,34.6,4)
  if n.startswith('Breeches'):
   y-=3.6*clamp((-y+6)/11)*ga(z,33,4)
  if n.startswith('Face'):
   # Round the projecting nose in depth; widen the end relative to the bridge.
   if y < -25 and 66<z<73.8 and abs(x)<7:
    u=clamp((-y-25)/8);x*=.83+.39*u;z+=(z-70)*(.28*u);y+=.75*u
   # Pull the projecting lip band and its corners back into the cheek plane.
   w=ga(z,64.2,3.6)*clamp((-y-19)/5)
   x-=.13*(x-.9)*w;z+=.95*ga(z,60.4,2.8)*w;y+=.8*w
  if n.startswith('Tooth'):
   x=.9+(x-.9)*.90;z+=.12;y+=.65
  if n.startswith('Arched brow'):
   z-=1.1*ga(abs(x),7,5);y-=.25
  if n.startswith('Cap'):
   z+=1.4*ga(z,78,4)*clamp((-y-13)/10);y+=.45*ga(z,78,4)
  if n.startswith('Beard'):
   y-=1.45*ga(z,53,9)*ga(x,-1,11);x+=.9*sin(z*.40)*ga(x,-1,8)
  if n.startswith('Nape curl'):
   y+=1.8*ga(z,73,4);z-=(.9+.9*sin(.4*x))*ga(z,72,4)
  v.co=(x,y,z)
for obj in objs:round_forms(obj)
# Paired ear bowls. Outer rim turns back into the head; the concha is recessed.
def ear(h):
 verts=[];faces=[];count=20
 for scale,depth in [(1,16.1),(.98,17.5),(.82,18.6),(.66,18.8),(.51,17.6),(.32,17.3),(.12,17.5)]:
  for i in range(count):
   t=2*pi*i/count
   verts.append((h*(depth+.45*cos(t)), -9.7+scale*(3.2*cos(t)+.5*sin(t)),72.4+scale*(5*sin(t)+.5*cos(t))))
 for j in range(6):
  for i in range(count):faces.append((j*count+i,j*count+(i+1)%count,(j+1)*count+(i+1)%count,(j+1)*count+i))
 faces += [tuple(range(count)),tuple(range(6*count,7*count))]
 mesh=bpy.data.meshes.new('Pinna');mesh.from_pydata(verts,[],faces);mesh.update()
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
 ob=bpy.data.objects.new('Ear | turned helix and concha',mesh);sc.collection.objects.link(ob);mesh.materials.append(bpy.data.materials['skin'])
 for f in mesh.polygons:f.use_smooth=True
 mod=ob.modifiers.new('Rounded ear rim','SUBSURF');mod.levels=2
for ob in list(objs):
 if ob.name.startswith('Ear | helix'):objs.remove(ob);bpy.data.objects.remove(ob,do_unlink=True)
for h in [-1,1]:ear(h)


def fine(n,p,nor,level):
 x,y,z=p;nx,ny,nz=nor
 if n.startswith('Face'):
  if ny>-.14:return 0
  if level==1:
   return 1.3*ga(x,10,4)*ga(z,72.1,2.4)+.85*ga(x,-10,4)*ga(z,70,2.5)-.6*ga(abs(x),4,1)*ga(z,68.6,1)
  return (-.44*ga(z,73.4+.10*(x-12),.36)*ga(x,12.6,2.5)
          -.37*ga(z,74.3+.33*(x-12),.35)*ga(x,12.9,2.2)
          -.49*ga(x,11.1+.24*(z-67),.55)*ga(z,67.5,2.4)
          -.59*ga(abs(x),3.5,1.25)*ga(z,69.3,.68)*clamp((-y-25)/3))
 if n.startswith(hair):
  if level==1:return .43*sin(x*1.3+.8*sin(z*.42)+z*.23)*clamp((-y-13)/5) if 'Nape' not in n else .42*sin(x*1.1+z*.57)
  return .15*cos(x*2.2+sin(z*.53)+.23*z)
 if n.startswith('Cap'):
  t=atan2(y+12,x);return (.85 if level==1 else .28)*ga(z,86,9)*sin(z*(.91 if level==1 else 1.8)+2.8*t+.65*sin(3*t))
 if n.startswith(('Sleeve','Breeches','Smock','Boot')):
  if n.startswith('Smock'):
   t=atan2(y,x);u=z-47-9*sin(t)-1.8*cos(2*t);return (.9 if level==1 else .31)*ga(u,4,7)*sin(u*(1 if level==1 else 1.8)+.8*cos(4*t))
  cx= (15 if 'Sleeve' in n else 9)*(1 if x>0 else -1)
  t=atan2(y-(-9 if 'Sleeve' in n else 4),x-cx);zc=49 if 'Sleeve' in n else 29 if 'Breeches' in n else 20
  return (.85 if level==1 else .3)*ga(z,zc,5.3)*sin((z-zc)*(.92 if level==1 else 1.7)+2*sin(t+.25*z))
 return 0
# Transfer first broad and then smaller surface displacements to successive sculpt grids.
prefix=('Face','Beard','Arched brow','Upswept','Temple curl','Nape curl','Cap','Smock','Sleeve','Breeches','Boot')
for o in objs:
 if not o.name.startswith(prefix):continue
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
 o.modifiers.clear()
 bm=bmesh.new();bm.from_mesh(o.data);loose=[v for v in bm.verts if not v.link_faces]
 if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
 bm.to_mesh(o.data);bm.free()
 mod=o.modifiers.new('Sculpt levels | form, folds, relief','MULTIRES')
 for lev in (1,2):
  bpy.ops.object.multires_subdivide(modifier=mod.name,mode='CATMULL_CLARK')
  mod.levels=lev;dg=bpy.context.evaluated_depsgraph_get()
  me=bpy.data.meshes.new_from_object(o.evaluated_get(dg));tmp=bpy.data.objects.new('Level transfer',me);sc.collection.objects.link(tmp)
  delta=[v.normal.copy()*fine(o.name,v.co,v.normal,lev) for v in me.vertices]
  for v,d in zip(me.vertices,delta):v.co+=d
  tmp.select_set(True);me.update();result=bpy.ops.object.multires_reshape(modifier=mod.name)
  if 'FINISHED' not in result:raise RuntimeError(o.name)
  bpy.data.objects.remove(tmp,do_unlink=True);bpy.data.meshes.remove(me)
 mod.sculpt_levels=2;mod.render_levels=2
# Short ivory catchlight, anchored into the open iris.
bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=12,location=(-6.45,-25.1,74.46))
glint=bpy.context.object;glint.name='Eye | catchlight';glint.scale=(.44,.46,.41);glint.data.materials.append(bpy.data.materials['tooth'])
cam=sc.camera
def view(pos,aim=(0,0,54),scale=119):
 cam.location=pos;cam.rotation_euler=(Vector(aim)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
def render(name):sc.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
view((0,-230,54));render('front')
view((230,0,54));render('profile')
view((0,230,54));render('rear')
view((50,-230,89),(0,-14,71),53);render('portrait')
# A second studio setup reveals the surface relief in softer light.
sc.render.engine='CYCLES';sc.cycles.samples=12;sc.cycles.use_denoising=True
sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.57,.64,.76,1);sc.world.node_tree.nodes['Background'].inputs[1].default_value=.46
for name,power,size,pos in [('Warm softbox',220000,95,(-75,-130,170)),('Fill',105000,85,(90,-65,100)),('Rim',180000,75,(30,88,130))]:
 bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.name=name;o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(Vector((0,0,55))-o.location).to_track_quat('-Z','Y').to_euler()
sc.view_settings.view_transform='AgX';sc.view_settings.exposure=0
view((33,-230,76));render('studio')
head=next(o for o in objs if o.name.startswith('Face'));bpy.ops.object.select_all(action='DESELECT');head.select_set(True);bpy.context.view_layer.objects.active=head
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Clive-Refined.blend'))

import bpy as b
objs=[o for o in b.context.scene.objects if o.type=='MESH']
b.ops.object.select_all(action='DESELECT')
for o in objs:o.select_set(True)
b.context.view_layer.objects.active=objs[0];b.ops.object.convert(target='MESH');b.ops.object.join();o=b.context.object;o.data.remesh_voxel_size=.22;b.ops.object.voxel_remesh()
bm=bmesh.new();bm.from_mesh(o.data);remaining=set(bm.verts);groups=[]
while remaining:
 v=remaining.pop();g=[v]
 for v in g:
  for ed in v.link_edges:
   w=ed.other_vert(v)
   if w in remaining:remaining.remove(w);g.append(w)
 groups.append(g)
groups.sort(key=len,reverse=True)
print('Shell sizes:',[len(g) for g in groups[:20]])
if len(groups)>1:bmesh.ops.delete(bm,geom=[v for g in groups[1:] for v in g],context='VERTS')
print('Nonmanifold edges:',sum(not e.is_manifold for e in bm.edges));bm.to_mesh(o.data);bm.free();b.ops.wm.stl_export(filepath=str(out/'Clive-Refined.stl'),export_selected_objects=True)