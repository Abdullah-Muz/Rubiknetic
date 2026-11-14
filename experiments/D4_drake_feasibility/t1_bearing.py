"""D4 / T1 — UNSCORED Drake feasibility: can hydroelastic contact represent a concave spherical
bearing at sub-0.1 mm clearance, which MuJoCo convex collision could not (D3)?

A compliant sphere (R = 24.95 mm, 3 g) sits inside a rigid NON-CONVEX spherical cap cup (inner
R = 25.0 mm, so 0.05 mm radial clearance). It is pressed into the cup with 3 N, like the centre
spring tension, and spun about the cup axis by a ramped torque. Reported: penetration proxy
(pressure and contact area), rotation smoothness (speed ripple), and wall time per simulated
second.

Runs in the separate Drake venv (drake 1.58.0), not the project env.
"""
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import trimesh
from pydrake.all import (AddCompliantHydroelasticProperties, AddContactMaterial, AddMultibodyPlantSceneGraph,
                         AddRigidHydroelasticProperties, CoulombFriction, DiagramBuilder, ExternallyAppliedSpatialForce,
                         ContactModel, Mesh, ProximityProperties, RigidTransform, Simulator, SpatialForce,
                         SpatialInertia, UnitInertia, Sphere, LeafSystem, AbstractValue)

R_IN, R_OUT, THETA = 0.0250, 0.0270, np.radians(50)
R_BALL = float(sys.argv[1]) if len(sys.argv) > 1 else 0.02495
DT = float(sys.argv[2]) if len(sys.argv) > 2 else 1e-3

# rigid cup: a spherical cap shell (concave inner surface), by revolving an annular sector profile
n = int(sys.argv[3]) if len(sys.argv) > 3 else 64
inner = [(R_IN * np.sin(t), R_IN * np.cos(t)) for t in np.linspace(0, THETA, n)]
outer = [(R_OUT * np.sin(t), R_OUT * np.cos(t)) for t in np.linspace(THETA, 0, n)]
profile = np.array(inner + outer)
cup = trimesh.creation.revolve(profile, sections=int(sys.argv[4]) if len(sys.argv) > 4 else 256)
if cup.volume < 0:
    cup.invert()
tmp = Path(tempfile.mkdtemp())
cup.export(tmp / "cup.obj")
print(f"cup: {len(cup.faces)} triangles, watertight {cup.is_watertight}, clearance {(R_IN - R_BALL) * 1e3:.3f} mm")

builder = DiagramBuilder()
plant, sg = AddMultibodyPlantSceneGraph(builder, time_step=DT)
plant.set_contact_model(ContactModel.kHydroelasticWithFallback)
world = plant.world_body()
rp = ProximityProperties()
AddRigidHydroelasticProperties(0.0005, rp)
AddContactMaterial(dissipation=5.0, friction=CoulombFriction(0.2, 0.2), properties=rp)
plant.RegisterCollisionGeometry(world, RigidTransform(), Mesh(str(tmp / "cup.obj")), "cup", rp)
ball = plant.AddRigidBody("ball", SpatialInertia(0.003, np.zeros(3), UnitInertia.SolidSphere(R_BALL)))
cp = ProximityProperties()
AddCompliantHydroelasticProperties(resolution_hint=float(sys.argv[5]) if len(sys.argv) > 5 else 0.002, hydroelastic_modulus=5e7, properties=cp)
AddContactMaterial(dissipation=5.0, friction=CoulombFriction(0.2, 0.2), properties=cp)
plant.RegisterCollisionGeometry(ball, RigidTransform(), Sphere(R_BALL), "ball", cp)
plant.mutable_gravity_field().set_gravity_vector([0, 0, 0])
plant.Finalize()


class Push(LeafSystem):
    """3 N push along +z into the cup, plus a torque about z ramped 0 -> 0.05 N m over 1 s."""
    def __init__(self):
        super().__init__()
        self.DeclareAbstractOutputPort("f", lambda: AbstractValue.Make([ExternallyAppliedSpatialForce()]), self.calc)

    def calc(self, ctx, out):
        t = ctx.get_time()
        f = ExternallyAppliedSpatialForce()
        f.body_index = ball.index()
        f.F_Bq_W = SpatialForce(np.array([0, 0, 0.05 * min(1.0, t)]), np.array([0, 0, 3.0]))
        out.set_value([f])


push = builder.AddSystem(Push())
builder.Connect(push.get_output_port(), plant.get_applied_spatial_force_input_port())
diagram = builder.Build()
sim = Simulator(diagram)
ctx = sim.get_mutable_context()
pctx = plant.GetMyMutableContextFromRoot(ctx)
plant.SetFreeBodyPose(pctx, ball, RigidTransform())
sim.Initialize()

ts, z, wz = [], [], []
t0 = time.perf_counter()
for k in range(1, 201):
    sim.AdvanceTo(k * 0.01)
    q = plant.GetPositions(pctx)
    v = plant.GetVelocities(pctx)
    ts.append(k * 0.01)
    z.append(q[6])
    wz.append(v[2])
wall = time.perf_counter() - t0
z, wz = np.array(z), np.array(wz)
print(f"simulated 2.0 s in {wall:.2f} s wall ({2.0 / wall:.2f}x real time, {2.0 / DT / wall:.0f} steps/s)")
print(f"ball centre z: after settle {z[20] * 1e3:+.4f} mm, final {z[-1] * 1e3:+.4f} mm "
      f"(sphere moves up 0.05 mm to touch; beyond that = penetration into the cup)")
print(f"spin rate: at 1.0 s {np.degrees(wz[99]):.1f} deg/s, at 2.0 s {np.degrees(wz[-1]):.1f} deg/s")
acc = np.diff(wz[100:]) / 0.01
print(f"angular acceleration 1-2 s (constant torque): mean {np.degrees(acc.mean()):.0f} deg/s^2, "
      f"std {np.degrees(acc.std()):.1f} (a smooth bearing gives low std, a faceted one shows ripple)")
