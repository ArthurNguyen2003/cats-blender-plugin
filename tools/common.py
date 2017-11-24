# MIT License

# Copyright (c) 2017 GiveMeAllYourCats

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the 'Software'), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Code author: GiveMeAllYourCats
# Repo: https://github.com/michaeldegroot/cats-blender-plugin
# Edits by:

import bpy
import globs

from difflib import SequenceMatcher
from mathutils import Vector
from math import degrees


def get_armature():
    # NOTE: what if there are two armatures?
    for object in bpy.data.objects:
        if object.type == 'ARMATURE':
            return object


def unhide_all():
    for object in bpy.data.objects:
        object.hide = False


def unselect_all():
    for object in bpy.data.objects:
        object.select = False


def select(obj):
    bpy.context.scene.objects.active = obj
    obj.select = True


def remove_empty():
    unhide_all()
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.data.objects:
        if obj.type == 'EMPTY':
            bpy.context.scene.objects.active = bpy.data.objects[obj.name]
            obj.select = True
            bpy.ops.object.delete(use_global=False)

        bpy.ops.object.select_all(action='DESELECT')


def get_bone_angle(p1, p2):
    try:
        ret = degrees((p1.head - p1.tail).angle(p2.head - p2.tail))
    except ValueError:
        ret = 0

    return ret


def remove_unused_vertex_groups():
    unselect_all()
    for ob in bpy.data.objects:
        if ob.type == 'MESH':
            ob.update_from_editmode()

            vgroup_used = {i: False for i, k in enumerate(ob.vertex_groups)}

            for v in ob.data.vertices:
                for g in v.groups:
                    if g.weight > 0.0:
                        vgroup_used[g.group] = True

            for i, used in sorted(vgroup_used.items(), reverse=True):
                if not used:
                    ob.vertex_groups.remove(ob.vertex_groups[i])


def find_center_vector_of_vertex_group(mesh_name, vertex_group):
    mesh = bpy.data.objects[mesh_name]

    group_lookup = {g.index: g.name for g in mesh.vertex_groups}
    verts = {name: [] for name in group_lookup.values()}
    for v in bpy.context.object.data.vertices:
        for g in v.groups:
            verts[group_lookup[g.group]].append(v)

    # Find the average vector point of the vertex cluster
    divide_by = len(verts[vertex_group])
    total = Vector()

    if divide_by == 0:
        return False

    for vertice in verts[vertex_group]:
        total += vertice.co

    average = total / divide_by

    return average


def get_meshes(self, context):
    choices = []

    for object in bpy.context.scene.objects:
        if object.type == 'MESH':
            choices.append((object.name, object.name, object.name))

    bpy.types.Object.Enum = sorted(choices, key=lambda x: x[0])
    return bpy.types.Object.Enum


def get_bones(self, context):
    choices = []
    armature = get_armature().data

    for bone in armature.bones:
        choices.append((bone.name, bone.name, bone.name))

    bpy.types.Object.Enum = sorted(choices, key=lambda x: x[0])

    return bpy.types.Object.Enum


def get_shapekeys(self, context):
    choices = []

    if hasattr(bpy.data.objects[context.scene.mesh_name_eye].data, 'shape_keys'):
        if hasattr(bpy.data.objects[context.scene.mesh_name_eye].data.shape_keys, 'key_blocks'):
            for shapekey in bpy.data.objects[context.scene.mesh_name_eye].data.shape_keys.key_blocks:
                choices.append((shapekey.name, shapekey.name, shapekey.name))

    bpy.types.Object.Enum = sorted(choices, key=lambda x: x[0])

    return bpy.types.Object.Enum


def fix_armature_name():
    get_armature().name = 'Armature'
    get_armature().data.name = 'Armature'


def get_texture_sizes(self, context):
    bpy.types.Object.Enum = [
        ("1024", "1024 (low)", "1024"),
        ("2048", "2048 (medium)", "2048"),
        ("4096", "4096 (high)", "4096")
    ]

    return bpy.types.Object.Enum


def get_parent_root_bones(self, context):
    armature = get_armature().data
    check_these_bones = []
    bone_groups = {}
    choices = []

    # Get cache if exists
    if len(globs.root_bones_choices) >= 1:
        return globs.root_bones_choices

    for bone in armature.bones:
        check_these_bones.append(bone.name)

    ignore_bone_names_with = [
        'finger',
        'chest',
        'leg',
        'arm',
        'spine',
        'shoulder',
        'neck',
        'knee',
        'eye',
        'toe',
        'head',
        'teeth',
        'thumb',
        'wrist',
        'ankle',
        'elbow',
        'hips',
        'twist',
        'shadow',
        'hand',
        'rootbone'
    ]

    # Find and group bones together that look alike
    # Please do not ask how this works
    for rootbone in armature.bones:
        for ignore_bone_name in ignore_bone_names_with:
            if ignore_bone_name in rootbone.name.lower():
                break
        for bone in armature.bones:
            if bone.name in check_these_bones:
                m = SequenceMatcher(None, rootbone.name, bone.name)
                if m.ratio() >= 0.70:
                    accepted = False
                    if bone.parent is not None:
                        for child_bone in bone.parent.children:
                            if child_bone.name == rootbone.name:
                                accepted = True

                    check_these_bones.remove(bone.name)
                    if accepted:
                        if rootbone.name not in bone_groups:
                            bone_groups[rootbone.name] = []
                        bone_groups[rootbone.name].append(bone.name)

    for rootbone in bone_groups:
        # NOTE: user probably doesn't want to parent bones together that have less then 2 bones
        if len(bone_groups[rootbone]) >= 2:
            choices.append((rootbone, rootbone.replace('_R', '').replace('_L', '') + ' (' + str(len(bone_groups[rootbone])) + ' bones)', rootbone))

    bpy.types.Object.Enum = choices

    # set cache
    globs.root_bones = bone_groups
    globs.root_bones_choices = choices

    return bpy.types.Object.Enum