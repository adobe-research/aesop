# !/usr/bin/python
# -*- coding: utf-8 -*-

import os
import json
import numpy as np
import pandas as pd
import pdb
import random
from PIL import Image
import math
import copy
import argparse
from PIL import Image, ImageDraw, ImageFont

def get_deform_xy_for_body_parts(config, human_config, name, objx, objy, depth, flip, rotations):
    
    depth_scales = [1.0]
    for i in range(1, config['numZSize']):
        depth_scales.append(
            depth_scales[i - 1] * config['zSizeDecay'])
            
    cur_obj_config = human_config[name]
    scale = cur_obj_config['globalScale'] * depth_scales[depth]

    partidxlist = cur_obj_config['partIdxList']
    num_body_parts = len(partidxlist)
    bodystuff = cur_obj_config['body']
    deformx = [0] * num_body_parts
    deformy = [0] * num_body_parts
    # get deformx and deformy of torso
    deformx[partidxlist['Torso']] = objx / scale
    deformy[partidxlist['Torso']] = objy / scale
    for partidx in range(num_body_parts):
        curpart = bodystuff[partidx]['part']
        parent = bodystuff[partidx]['parent']
        if partidx > 0:
            parent_idx = partidxlist[parent]
            prevr = rotations[parent_idx]
            if flip == 1:
                rotmat = [math.cos(prevr), -math.sin(prevr), math.sin(prevr), math.cos(prevr)]
                tempx = bodystuff[parent_idx]['childX'] - bodystuff[partidx]['parentX']
                tempy = bodystuff[partidx]['parentY'] - bodystuff[parent_idx]['childY']
                deformx[partidxlist[curpart]] = rotmat[0] * tempx + rotmat[1] * tempy + deformx[parent_idx]
                deformy[partidxlist[curpart]] = rotmat[2] * tempx + rotmat[3] * tempy + deformy[parent_idx]
            else:
                rotmat = [math.cos(prevr), -math.sin(prevr), math.sin(prevr), math.cos(prevr)]
                tempx = bodystuff[partidx]['parentX'] - bodystuff[parent_idx]['childX']
                tempy = bodystuff[partidx]['parentY'] - bodystuff[parent_idx]['childY']
                deformx[partidxlist[curpart]] = rotmat[0] * tempx + rotmat[1] * tempy + deformx[parent_idx]
                deformy[partidxlist[curpart]] = rotmat[2] * tempx + rotmat[3] * tempy + deformy[parent_idx]
    return deformx, deformy

def get_scene_from_story_dict(story_dict, data_root):
    # convert direct or conv feat to jsondict which can then be converted to scene json
    '''
    INPUT:
        story_dict: json in same format as story_dict obtained when doing scene2dict
                    {
                    'bg': [1,2,1],
                    'text': ['text1', 'text2', 'text3'],
                    'title': 'title',
                    'theme': ['funny'],
                    'image_data': [
                                    {
                                     idx: 0,
                                     x: 300,
                                     y: 450,
                                     depth: 2,
                                     flip: 0,
                                     pose: 3,
                                     expression: None,
                                    }, 
                              ....]
                     }
                     # idx is object index from ./data/objects.json (you can define your own. Change code accordingly)
                     # pose will be list of rotation values when clipart is human
    OUTPUT:
        scenejson: scene.json in format necessary for renderer to render.
    '''
    # read sample scene and config file
    sample_scene = json.load(open('{}/sample/scene.json'.format(data_root)))
    sample_meta = json.load(open('{}/sample/meta.json'.format(data_root)))
    config = json.load(open('{}/scene_config_files/abstract_scenes_v002_data_scene_config.json'.format(data_root)))['Extended-All']
    tempconf = json.load(open('{}/scene_config_files/abstract_scenes_v002_data_human_deform.json'.format(data_root)))['type']
    human_config = dict()
    for human_type in tempconf:
        human_config[human_type['name']] = human_type
        
    objdict = json.load(open('{}/objects.json'.format(data_root)))

    # init output files
    output_scene = copy.deepcopy(sample_scene)
    output_meta = copy.deepcopy(sample_meta)

    # Finish with meta.json
    output_meta['bg'] = story_dict['bg']
    output_meta['story'] = story_dict['text']
    output_meta['title'] = story_dict['title']
    output_meta['theme'] = story_dict['theme']
    
    # Compile scene.json
    for panelnum in range(len(story_dict['image_data'])):
        
        panel = story_dict['image_data'][panelnum]

        # Get a maximum of three instances of each object and compile for ease
        seen_objs = dict()
        for obj in panel:
            # get all necessary data
            objname = objdict['i2o'][str(obj['idx'])]['name']
            # predict only a maximum of three instances of each object
            if objname in seen_objs:
                if len(seen_objs[objname]) == 3:
                    continue
            else:
                seen_objs[objname] = []
            objtype = objdict['i2o'][str(obj['idx'])]['type']
            objclass = objdict['i2o'][str(obj['idx'])]['class']
            objx = int(obj['x'])
            objy = int(obj['y'])
            objz = int(obj['depth'])
            objflip = int(obj['flip'])
            objpose = obj['pose']
            if objclass == 'human':
                objexpr = int(obj['expression'])
            else:
                objexpr = None
                if objpose is not None:
                    objpose = int(objpose)
            seen_objs[objname].append([objname, objtype, objx, objy, objz, objflip, objpose, objexpr])
        
        # Start putting objects in scene.json format
        output_scene[panelnum]['availableObject'] = []
        for curname in seen_objs:
            curobj_idx = len(output_scene[panelnum]['availableObject'])
            # get sample dict from GT
            for obj in range(len(sample_scene[panelnum]['availableObject'])):
                if sample_scene[panelnum]['availableObject'][obj]['instance'][0]['name'] == curname:
                    sample_obj = copy.deepcopy(sample_scene[panelnum]['availableObject'][obj])
                    for inst in range(3):
                        sample_obj['instance'][inst]['present'] = False
            # go through each predicted instance and fill in details
            for inst in range(len(seen_objs[curname])):
                if inst == 0:
                    output_scene[panelnum]['availableObject'].append(sample_obj)
                curobj = seen_objs[curname][inst]
                curname = curobj[0]
                output_scene[panelnum]['availableObject'][curobj_idx]['instance'][inst]['present'] = True
                curtype = sample_obj['instance'][inst]['type']
                curname = sample_obj['instance'][inst]['name']
                # get typeid
                if curobj[1] is not None:
                    output_scene[panelnum]['availableObject'][curobj_idx]['instance'][inst]['typeID'] = int(curobj[1])
                # get loc
                # curloc = self.index2coord(int(curobj[1]))
                output_scene[panelnum]['availableObject'][curobj_idx]['instance'][inst]['x'] = int(curobj[2])
                output_scene[panelnum]['availableObject'][curobj_idx]['instance'][inst]['y'] = int(curobj[3])
                # get depth
                output_scene[panelnum]['availableObject'][curobj_idx]['instance'][inst]['z'] = int(curobj[4])
                # get flip
                output_scene[panelnum]['availableObject'][curobj_idx]['instance'][inst]['flip'] = int(curobj[5])
                # get pose
                if curtype in ['largeObject', 'smallObject']:
                    pass
                elif curtype == 'animal':
                    output_scene[panelnum]['availableObject'][curobj_idx]['instance'][inst]['poseID'] = int(curobj[6])
                else:
                    curdeformx, curdeformy = get_deform_xy_for_body_parts(config, human_config, curname, curobj[2], curobj[3],
                                                                          curobj[4], curobj[5], curobj[6])
                    output_scene[panelnum]['availableObject'][curobj_idx]['instance'][inst][
                        'deformableGlobalRot'] = curobj[6]
                    output_scene[panelnum]['availableObject'][curobj_idx]['instance'][inst]['deformableX'] = curdeformx
                    output_scene[panelnum]['availableObject'][curobj_idx]['instance'][inst]['deformableY'] = curdeformy
                # get expression
                if curtype == 'human':
                    output_scene[panelnum]['availableObject'][curobj_idx]['instance'][inst]['expressionID'] = int(
                        curobj[7])
    return output_scene, output_meta


def get_obj_info(obj, data_root):
    # convert huge scene json file to a crisp dict of necessary info for each story
    '''
    INPUT:
        scene: scene json as in the dataset. Just the available objects dict.
    OUTPUT:
        panledata: list (objdict) where objdict has only necessary attriutes with correct representation
    '''
    objdict = json.load(open('{}/objects.json'.format(data_root)))
    cur_objdict = dict()
    # get name of object - one of the 158 names string
    cur_objdict['name'] = obj['name']
    # get class obj belongs to - human, animal, smallObject or largeObject
    cur_objdict['objclass'] = obj['type']

    # get universal idx of object type (290 objects including their types)
    if cur_objdict['objclass'].lower() in ['largeobject', 'smallobject']:
        cur_objdict['type_name'] = '{}--{}'.format(
            cur_objdict['name'], obj['typeID'])
        cur_objdict['idx'] = objdict['o2i'][cur_objdict['type_name']]
    else:
        cur_objdict['idx'] = objdict['o2i'][cur_objdict['name']]

    # get expression ID
    if cur_objdict['objclass'].lower() == 'human':
        cur_objdict['expression'] = obj['expressionID']
    else:
        cur_objdict['expression'] = None

    # get position of object in current panel - real valued number
    cur_objdict['x'] = obj['x']
    cur_objdict['y'] = obj['y']
    cur_objdict['depth'] = obj['z']
    cur_objdict['flip'] = obj['flip']

    # get pose
    if cur_objdict['objclass'].lower() == 'human':
        cur_objdict['pose'] = obj['deformableGlobalRot']
    elif cur_objdict['objclass'].lower() == 'animal':
        cur_objdict['pose'] = obj['poseID']
    else:
        cur_objdict['pose'] = None
    return cur_objdict

def scene2dict(cur_scene, data_root):
    # convert huge scene json file to a crisp dict of necessary info for each story
    '''
    INPUT:
        scene: scene json as in the dataset. Just the available objects dict.
    OUTPUT:
        panledata: list (objdict) where objdict has only necessary attriutes with correct representation
    '''
    # init stuff
    panel_size = [700, 400]
    config_folder = '{}/scene_config_files/'.format(data_root)
    scene_config_file = os.path.join(config_folder,
                                     cur_scene['sceneConfigFile'])
    with open(scene_config_file) as json_fileid:
        scene_config_data = json.load(json_fileid)
    cur_scene_type = cur_scene['sceneType']
    cur_scene_config = scene_config_data[cur_scene_type]
    def_z_size = cur_scene_config['defZSize']
    img_pad_num = cur_scene_config['imgPadNum']
    not_used = cur_scene_config['notUsed']
    num_z_size = cur_scene_config['numZSize']
    num_depth0 = cur_scene_config['numDepth0']
    num_depth1 = cur_scene_config['numDepth1']
    num_flip = cur_scene_config['numFlip']

    object_type_data = cur_scene_config['objectTypeData']
    object_type_order = []
    num_obj_type_show = {}
    for obj_el in object_type_data:
        cur_name = obj_el['nameType']
        object_type_order.append(cur_name)
        num_obj_type_show[cur_name] = obj_el['numShow']

    cur_avail_obj = cur_scene['availableObject']
    cur_z_scale = [1.0]
    for i in range(1, num_z_size):
        cur_z_scale.append(
            cur_z_scale[i - 1] * cur_scene_config['zSizeDecay'])

    paneldata = []
    seen_objs = dict()
    # do the actual extraction. In the same order as done during rendering.
    for k in reversed(range(0, num_depth0)):
        for j in reversed(range(0, num_z_size + 1)):
            for L in reversed(range(0, num_depth1)):
                for i in range(0, len(cur_avail_obj)):
                    if cur_avail_obj[i]['instance'][0]['depth0'] == k:
                        if cur_avail_obj[i]['instance'][0]['name'] not in seen_objs:
                            if cur_avail_obj[i]['instance'][0]['depth1'] == L:
                                seen_objs[cur_avail_obj[i]['instance'][0]['name']] = [k, L]
                        for m in range(0, cur_avail_obj[i]['numInstance']):
                            cur_obj = cur_avail_obj[i]['instance'][m]
                            if (cur_obj['present'] is True and
                                    cur_obj['z'] == j and
                                    cur_obj['depth1'] == L):
                                x = cur_obj['x']
                                y = cur_obj['y']
                                # get clipped pos
                                if x < 0:
                                    x = 0
                                elif x > panel_size[0] - 1:
                                    x = panel_size[0] - 1
                                else:
                                    pass
                                if y < 0:
                                    y = 0
                                elif y > panel_size[1] - 1:
                                    y = panel_size[1] - 1
                                else:
                                    pass
                                cur_obj['x'] = x
                                cur_obj['y'] = y
                                curobjdict = get_obj_info(cur_obj, data_root)
                                curobjdict['depth0'] = k
                                curobjdict['depth1'] = L
                                paneldata.append(curobjdict)
    return paneldata, cur_scene_type

def get_data_for_one_story(submission_dir, data_root):
    
    '''
    INPUT:
        submission_dir: path to story directory (e.g. ./data/stories/0000)
    OUTPUT:
        storydict: json that has only necessary attriutes with correct representation
    '''
    storydict = dict()
    # get submission ID
    cur_subid = submission_dir.split('/')[-1]

    # init text and image panels
    cur_image_story = []
    cur_scene_type = []
    cur_scene_images = []

    # load the json files
    curscene = json.load(open(os.path.join(submission_dir, 'scene.json'), 'r'))
    curmeta = json.load(open(os.path.join(submission_dir, 'meta.json'), 'r'))

    # get data from scene.json
    for idx in range(len(curscene)):
        paneldata, scenetype = scene2dict(curscene[idx])
        cur_image_story.append(paneldata)
        cur_scene_type.append(scenetype)
        # get rendered image path
        # uncomment below lines if using redraw retell etc
        imagename = '{}/images/{}/panel_{}.png'.format(data_root, cur_subid, idx)
        cur_scene_images.append(imagename)

    # populate storydict with all necessary data
    storydict['storyid'] = cur_subid
    storydict['theme'] = curmeta['theme']
    storydict['title'] = curmeta['title']
    storydict['image_data'] = cur_image_story
    storydict['text'] = curmeta['story']
    storydict['bg'] = curmeta['bg']
    storydict['image_path'] = cur_scene_images
    storydict['scenetype'] = cur_scene_type
    return storydict


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description='aesop_utils')
    parser.add_argument('--input_path', type=str,
                       help='path to story folder if scene2dict and path to json file for dict2scene')
    parser.add_argument('--output_path', type=str,
                       help='path to where the generated jsons will be saved')
    parser.add_argument('--data_root', type=str, default='./data',
                       help='path to data root')
    parser.add_argument('--scene2dict', action='store_true',
                        help='Flag to convert scene json to clean dict')
    parser.add_argument('--dict2scene', action='store_true',
                        help='Flag to convert clean dict (possibly from model prediction) to scene.json and meta.json')
    
    args = parser.parse_args()

    if args.scene2dict:
        # input path example ./data/stories/0000
        # output path example ./
        out_json = get_data_for_one_story(args.input_path, args.data_root)
        storyid = args.input_path.split('/')[-1]
        outpath = '{}/{}'.format(args.output_path, storyid)
        if not os.path.isdir(outpath):
            os.makedirs(outpath)
        json.dump(out_json, open('{}/story_dict.json'.format(outpath), 'w'))

    if args.dict2scene:
        # input path example ./data/stories/0000/story_dict.json (output of scene2dict or model)
        # output path example ./
        if isinstance(args.input_path, str):
            inputfile = json.load(open(args.input_path))
        elif isinstance(args.input_path, dict):
            inputfile = copy.deepcopy(inputfile)
        else:
            pass
        scene, meta = get_scene_from_story_dict(inputfile, args.data_root)
        storyid = args.input_path.split('/')[-2]
        outpath = '{}/{}'.format(args.output_path, storyid)
        if not os.path.isdir(outpath):
            os.makedirs(outpath)
        json.dump(scene, open('{}/scene.json'.format(outpath), 'w'))
        json.dump(meta, open('{}/meta.json'.format(outpath), 'w'))
