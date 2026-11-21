import bpy as b, math as m, os, bmesh
from mathutils import Vector
from math import sin,cos,pi,exp,sqrt
b.ops.wm.read_factory_settings(use_empty=True)
sc=b.context.scene
sc.unit_settings.system='METRIC';sc.unit_settings.scale_length=.001
colors={'skin':(.87,.49,.26),'rose':(.83,.33,.18),'hair':(.95,.81,.57),'hat':(.58,.036,.018),'blue':(.025,.12,.31),'boot':(.26,.095,.032),'base':(.82,.67,.43),'mouth':(.105,.034,.018),'tooth':(.99,.9,.72),'eye':(.98,.9,.73),'iris':(.23,.095,.022),'pupil':(.035,.016,.009),'brass':(.65,.38,.1)}
mats={}
for k,c in colors.items():
 a=b.data.materials.new(k);a.diffuse_color=(*c,1);a.use_nodes=True
 bs=a.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*c,1);bs.inputs['Roughness'].default_value=.31;mats[k]=a
def mesh(n,v,f,k,indices=None):
 me=b.data.meshes.new(n);me.from_pydata(v,[],f);me.update();o=b.data.objects.new(n,me);sc.collection.objects.link(o)
 keys=[k] if not indices else list(colors)
 for key in keys:me.materials.append(mats[key])
 for i,p in enumerate(me.polygons):
  p.use_smooth=True
  if indices:p.material_index=keys.index(indices[i])
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(me);bm.free()
 mod=o.modifiers.new('Editable Catmull-Clark cage','SUBSURF');mod.levels=2;mod.render_levels=2
 return o
def surface(n,rows,k):
 N=len(rows[0]);f=[]
 for j in range(len(rows)-1):
  for i in range(N):f.append((j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i))
 f.extend([tuple(range(N)),tuple(range((len(rows)-1)*N,len(rows)*N))])
 return mesh(n,sum(rows,[]),f,k)
def loft(n,levels,k,N=20,warp=None):
 rows=[]
 for j,(x,y,z,a,d) in enumerate(levels):
  row=[]
  for i in range(N):
   t=2*pi*i/N;w=warp(j,t) if warp else 0;row.append((x+a*cos(t),y+d*sin(t),z+w))
  rows.append(row)
 return surface(n,rows,k)
def sweep(n,path,k,flute=0,N=12):
 rows=[]
 for j,(x,y,z,a,d) in enumerate(path):
  dr=(Vector(path[min(len(path)-1,j+1)][:3])-Vector(path[max(0,j-1)][:3])).normalized()
  side=Vector((0,1,0)).cross(dr)
  if side.length<.01:side=Vector((1,0,0))
  side.normalize();depth=dr.cross(side).normalized()
  if n.startswith('Cap') and j<13:
   side=Vector((1,0,.055*sin(j*.9)));depth=Vector((0,1,-.19 if j<6 else -.07))
  row=[]
  for i in range(N):
   t=2*pi*i/N;g=1+flute*cos(5*t+.21*j);row.append(Vector((x,y,z))+g*(a*cos(t)*side+d*sin(t)*depth))
  rows.append(row)
 return surface(n,rows,k)
# Box front with selectively inset quad patches; continuous through sides to back.
X=[-17,-14,-11,-8,-5,-2,0,2,5,8,11,14,17];Z=[60,62,64,66,68,70,72,74,76,78,80,83]
V=[];F=[];M=[]
def vert(p):
 x,y,z=p;f=1-.45*max(0,min(1,(z-77)/5));V.append((x*f,-12+(y+12)*f,z));return len(V)-1
def face(p,k='skin'):F.append(p);M.append(k)
def cage(x,z,back):
 w=1-.25*((z-72)/13)**2
 return (x*w,(-22+6*(abs(x)/17)**2+2.6*((z-72)/12)**2-2*exp(-((abs(x)-11)/4)**2-((z-70)/3)**2)) if not back else -2-5*(abs(x)/17)**2,z)
A={};B={}
for j,z in enumerate(Z):
 for i,x in enumerate(X):A[i,j]=vert(cage(x,z,0));B[i,j]=vert(cage(x,z,1))
regions=[(1,5,6,9,'open'),(7,11,6,9,'wink'),(4,8,4,6,'nose'),(2,10,1,4,'grin'),(1,4,4,6,'cheek'),(8,11,4,6,'cheek')]
def border(a,c,d,e):return [(i,d) for i in range(a,c)]+[(c,j) for j in range(d,e)]+[(i,e) for i in range(c,a,-1)]+[(a,j) for j in range(e,d,-1)]
for j in range(len(Z)-1):
 for i in range(len(X)-1):
  q=border(i,i+1,j,j+1);face([B[p] for p in q])
  if not any(a<=i<c and d<=j<e for a,c,d,e,n in regions):face([A[p] for p in q])
q=border(0,len(X)-1,0,len(Z)-1)
for i,p in enumerate(q):
 t=q[(i+1)%len(q)];face([A[p],A[t],B[t],B[p]])
for a,c,d,e,n in regions:
 q=border(a,c,d,e);prev=[A[p] for p in q];xc=(X[a]+X[c])/2;zc=(Z[d]+Z[e])/2
 angles=[m.atan2((Z[j]-zc)/(Z[e]-zc),(X[i]-xc)/(X[c]-xc)) for i,j in q]
 if n=='nose':rings=[(0,70,5.6,3,-24,'skin'),(0,69.8,5.8,3.9,-28,'rose'),(0,69.6,5,3.7,-31.8,'rose'),(0,69.8,3.3,2.8,-34,'rose'),(0,69.9,1.2,1,-34.8,'rose')]
 elif n=='cheek':rings=[(xc,70.2,4.9,2.7,-22.5,'skin'),(xc,70.3,3.9,2.4,-23.7,'skin'),(xc,70.5,2.4,1.6,-24.6,'skin')]
 elif n=='grin':rings=[(1,65,10,3.6,-21.7,'skin'),(1,65,9.1,3,-23,'skin'),(1,65,8.4,2.5,-23.1,'rose'),(1,65,8,2.3,-22.1,'mouth'),(1,65,6.7,1.5,-21.6,'mouth')]
 elif n=='open':rings=[(-7.3,74.2,4.8,3,-22.9,'skin'),(-7.3,73.9,4.1,2.35,-24.2,'skin'),(-7.3,73.9,3.6,1.85,-24.1,'mouth'),(-7.3,73.9,3.4,1.75,-24.4,'eye'),(-6.7,73.9,1.65,1.58,-25.3,'eye'),(-6.6,73.9,1.42,1.47,-25.1,'iris'),(-6.6,73.9,.8,1,-25.3,'pupil')]
 else:rings=[(7.3,74,4.6,2.8,-22.6,'skin'),(7.4,73.8,4.1,1.45,-24.1,'skin'),(7.4,73.8,3.7,.47,-24.25,'skin'),(7.4,73.8,3.5,.23,-23.8,'mouth')]
 for cx,cz,rx,rz,y,k in rings:
  nxt=[]
  for t in angles:
   x=cx+rx*cos(t);z=cz+rz*sin(t)
   if n=='grin':z+=1.6*cos(t)**2+1.45*cos(t)
   if n=='wink':z+=.65*sin(t)**2+.35*cos(t)
   if n=='grin': yoff=-3.4;z-=2.55;z+=.75*cos(t)**2
   elif n in ['open','wink']: yoff=min(1,rx/4)**2*(2.1*cos(t)**2+.55*cos(t)*(1 if n=='wink' else -1))
   else: yoff=0
   nxt.append(vert((x,y+yoff+.75*cos(t)**2,z)))
  for i,v in enumerate(prev):face([v,prev[(i+1)%len(q)],nxt[(i+1)%len(q)],nxt[i]],k)
  prev=nxt
 face(prev,k)
head=mesh('Face | box cage, paired eye loops, nose and smile',V,F,'skin',M)
# Folded cap follows a curved spine, with a heavy downturned tip.
sweep('Cap | rolled brim to hooked crown',[(0,-12,77,16,13),(0,-12,77.1,18.2,15),(0,-12,78,18.6,15.2),(-.6,-12,80,17.7,14.8),(-1.8,-12,82.5,15,13),(-2,-12,84,14.2,12),(-1,-11.7,85.2,15.2,12.9),(-.5,-11,87,15,12.6),(-1,-11,89,12,10),(-1,-10,91,10.6,9),(-1,-10,92,11.6,9.7),(0,-10,94.3,10,8.9),(2,-10,98,7.9,7.1),(5.5,-10,101.7,6.5,6.1),(9,-10,103,4.8,5),(12,-10,102,3.6,4),(13.6,-10,99.5,2.8,3.3),(13.2,-10,97.3,2.1,2.2),(12.6,-10,96.9,.9,1)],'hat',0,32)
def lock(n,path):return sweep(n,path,'hair',.095,20)
for h in [-1,1]:
 def mir(p):return [(h*x,y,z,a,d) for x,y,z,a,d in p]
 lock('Arched brow',mir([(1.2,-22,76.2,.5,.6),(2.6,-23.3,77,2.1,1.7),(5,-23.4,79.3,2.3,2),(8.7,-22,80,2.3,1.9),(11,-20.6,79,1.65,1.6),(13,-19.1,76.8,.6,.7)]))
 lock('Upswept moustache',mir([(0,-26,68,.8,1),(2,-27,67.8,2.2,2.2),(5,-27.6,66,2.5,2.5),(8.5,-26.3,65.6+h*.8,2.35,2.3),(11.6,-24.5,66.4+h*.9,2.1,2),(13.1,-23.4,68.8,1.5,1.6),(12.4,-23,70,.4,.5)]))
 for j in range(3):
  lock('Temple curl',mir([(12,-14+j*4,78-j,1.4,1.8),(15,-13+j*4,75-j,2.6,2.4),(17,-12+j*4,72-j,3,2.6),(19,-10+j*4,71-j,2,2),(20,-9+j*4,73-j,.55,.7)]))
 sweep('Ear | helix',mir([(15,-11,68,1.2,1.6),(17,-11,69,2.4,2.4),(18,-12,73,2.3,2.7),(18,-11,75,1.9,2),(16,-10,75,1,1)]),'skin')
# Beard is a single corrugated mantle with surface locks tapering into its curl.
loft('Beard | silhouette',[(2,-20,42,.6,.7),(1,-20,43,3,2),(-1,-20,45,5,3),(0,-19.6,49,8,4),(0,-18,54,12,5.5),(0,-17,59,14.8,6.4),(0,-16,63,15,6),(0,-15,65.5,13.5,4.5)],'hair')
for i in range(-4,5):
 x=i*3.15;u=abs(i)/4;end=42+16*u**1.5;y=-24.3+3.6*u
 lock('Beard | flowing lock',[(x,-17.6,65+3*u,1.2,1.1),(x*1.08,-20.5,63+3*u,3.3,2.6),(x*1.1+1,y,60+2*u,3.1,2.5),(x*.99+1.6,y-.4,56+4*u,2.7,2),(x*.92-1,y+.3,(end+55+4*u)/2,2.25,1.8),(x*.95-1,y+1,end+1.2,1.35,1.4),(x*.95+1,y+2,end,.35,.5)])
for i in range(-3,4):
 x=1.4+i*1.55;z=63.3+.13*x+.024*x*x
 loft('Tooth',[(x,-25.8,z-.9,.4,.3),(x,-26.35,z-.85,.85,.55),(x,-26.35,z+.8,.9,.58),(x,-25.8,z+1,.7,.4)],'tooth',8)
# Broad back. Pull rear hem upward to reveal seat, dropping front to waistband.
loft('Smock | lifted rear hem',[(0,1,45,19,23),(0,1,45.3,20.2,24),(0,1,47,20.8,24.5),(0,1,48.3,19.5,23.7),(0,1,50,20.4,24.4),(0,1,54,21,24),(0,0,60,20.5,22),(0,-2,66,17,18),(0,-5,69,11,13)],'blue',32,lambda j,t: [11,11,10.6,10,9,6,4,0,-1][j]*sin(t))
loft('Plinth | glazed foot',[(0,1,0,23,22),(0,1,.1,24,23),(0,1,.8,24.3,23.3),(0,1,9.5,23.4,22.4),(0,1,11,23,22),(0,1,11.3,21.8,20.8)],'base',40)
for h in [-1,1]:
 def side(n,lev,k,N=20):return loft(n,[(h*x,y,z,a,d) for x,y,z,a,d in lev],k,N)
 side('Seat | bent hip',[(8,9,31,5,7),(9,12,33,8,11),(9.4,15,36,10.2,14.2),(9.6,16,42,11.3,16.8),(9,15.5,47,11.2,17.3),(8.6,13.5,53,10.7,15.3),(8,11,57,9.6,13),(7,7,59,6,8)],'skin')
 side('Boot | toe sole and shaft',[(9,-1,11,7.9,13.7),(9,-1,11.4,8.4,14.1),(9,-1,12.4,8.6,14.2),(9,-1,13.2,8.1,13.6),(9,-2,13.9,8.3,13.9),(9,-2,16.8,8.1,13.1),(9,0,18.5,7.3,10.2),(9,3,19.5,6.5,7.6),(9,3.7,20.5,7.2,7.8),(9,3.8,22,6.5,7),(9,4,25,7,7.5)],'boot')
 side('Breeches | pooled folds',[(9,4,23,6.5,7.2),(9,4,23.4,8.4,8.6),(9,4.2,25,9,9),(9,4.4,26.4,7.7,8),(9,4.7,27.2,8.2,8.8),(9,5.4,28.3,9.5,10),(9,6,30,9.5,10.5),(9,6,31,8,9.8),(9,6.4,32.6,9.3,11),(9,6.7,34,9.6,11.3),(9,6.7,35.2,8.7,10.6)],'blue')
 side('Sleeve | elbow and cuff',[(14,-10,43.5,5.3,5.8),(14.4,-9.8,44,6.4,6.7),(15,-9.3,46,6.6,7),(15.1,-9.1,47.2,5.6,6.6),(15.9,-8.5,48.6,6.6,7.6),(16.4,-7.5,50,6.3,8),(16.7,-7,53,6.1,8.4),(16.3,-6,58,6,8),(15,-5,63,6,7),(13,-5,66,5,6),(12,-4,67,3,4)],'blue')
 sweep('Forearm into gripping hand',mir([(14.4,-10,46,4.6,5),(14,-11,43,4.6,4.9),(12.8,-12.4,40,4.2,4.4),(11.5,-13.7,37.8,3.75,3.8),(10,-14.1,35.5,4.7,3.8),(9.8,-14,33.8,4,3)]),'skin')
 for j in range(4):
  x=6.5+1.7*j
  sweep('Curled finger',mir([(x,-14.7,36.7,1.4,1.5),(x+.25,-16.3,35.4,1.45,1.6),(x,-16.6,33.7+.22*j,1.25,1.3),(x-.2,-15.3,33+.22*j,.85,.95)]),'skin')
 sweep('Thumb',mir([(7.4,-13.2,38,1.4,1.5),(6,-14.1,36.8,1.7,1.8),(5.7,-15.3,35,1.3,1.4)]),'skin')
loft('Waistband | pulled forward',[(0,-3,31,14,11),(0,-3,32,16,12),(0,-3,34,16.8,12.6),(0,-3,35.2,16.8,12.6),(0,-3,35.8,16,12)],'blue')
# Tuck the beard beneath the lip and vary the curl at each lock.
for obj in sc.objects:
 if obj.name.startswith('Beard'):
  for v in obj.data.vertices:
   v.co.z-=max(0,1-abs(v.co.x)/11)*max(0,min(1,(v.co.z-54)/8))*5.5
 if obj.name.startswith(('Forearm','Curled finger','Thumb')):
  for v in obj.data.vertices:
   v.co.y-=5*max(0,min(1,(46-v.co.z)/9))
 if obj.name.startswith('Sleeve'):
  for v in obj.data.vertices:v.co.y-=2*max(0,min(1,(54-v.co.z)/9))
loft('Front trouser panel',[(0,1,31,13,10),(0,-1,32,15.7,12),(0,-1,34.5,16,14),(0,1,38,16,13),(0,3,42,16,13),(0,4,47,16,14)],'blue')
for z,y in [(37.6,-18.6),(40.8,-20.2)]:
 loft('Tunic button',[(0,y,z-.65,.55,.55),(0,y-.2,z,.82,.65),(0,y,z+.65,.55,.55)],'brass',10)
# Nape ringlets bridge the rear hat brim to the collar.
for j in range(-4,5):
 x=j*3.8;y=1-abs(j)*.95
 lock('Nape curl',[(x*.84,y-2,79,2,2),(x*.97,y,76,3.5,3),(x+1,y+2,73,3.3,3),(x+2,y+3,71,2.8,2.5),(x+3.5,y+3,71.6,1.35,1.3),(x+3.8,y+2.7,73,.5,.5)])

from pathlib import Path
out=Path(__file__).resolve().parent
sc.render.engine='BLENDER_WORKBENCH';sh=sc.display.shading;sh.color_type='MATERIAL';sh.light='STUDIO';sh.studiolight_rotate_z=.42;sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='WORLD';sh.cavity_valley_factor=1.3;sh.background_type='WORLD'
sc.world=b.data.worlds.new('Studio');sc.world.color=(.13,.14,.16)
sc.render.resolution_x=600;sc.render.resolution_y=680;sc.render.resolution_percentage=100
b.ops.object.camera_add();cam=b.context.object;sc.camera=cam;cam.data.type='ORTHO';cam.data.clip_end=1000
def view(pos,aim=(0,0,54),scale=119):
 cam.location=pos;cam.rotation_euler=(Vector(aim)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
view((45,-230,80))
for area in b.context.screen.areas:
 if area.type=='VIEW_3D':
  sp=area.spaces.active;sp.clip_end=1000;sp.region_3d.view_rotation=cam.rotation_euler.to_quaternion();sp.region_3d.view_location=(0,0,54);sp.region_3d.view_distance=156;sp.shading.color_type='MATERIAL'
b.ops.object.select_all(action='DESELECT');head.select_set(True);b.context.view_layer.objects.active=head
sc.render.image_settings.color_mode='RGB';sc.view_settings.view_transform='Standard';sc.view_settings.exposure=.55
b.ops.wm.save_as_mainfile(filepath=str(out/'Clive-SubD.blend'))
for name,pos in [('front',(0,-230,54)),('profile',(230,0,54)),('rear',(0,230,54)),('portrait',(50,-230,89)),('cage',(46,-230,80))]:
 view(pos,(0,-14,71) if name in ['portrait','cage'] else (0,0,54),53 if name in ['portrait','cage'] else 119)
 if name=='cage':
  for obj in sc.objects:
   if obj not in (head,cam):obj.hide_render=True
  copy=head.copy();copy.data=head.data.copy();sc.collection.objects.link(copy);copy.modifiers.clear();wire=copy.modifiers.new('Visible editable edges','WIREFRAME');wire.thickness=.18;wire.use_even_offset=False
  for slot in copy.material_slots:slot.material=mats['pupil']
  head.modifiers[0].render_levels=0
 sc.render.filepath=str(out/(name+'.png'));b.ops.render.render(write_still=True)
b.ops.wm.open_mainfile(filepath=str(out/'Clive-SubD.blend'))
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
print('Nonmanifold edges:',sum(not e.is_manifold for e in bm.edges));bm.to_mesh(o.data);bm.free();b.ops.wm.stl_export(filepath=str(out/'Clive-SubD.stl'),export_selected_objects=True)