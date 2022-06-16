# !/usr/bin/python
# -*- coding: utf-8 -*-

import json
import math
import os
from os import path, sep

from PIL import Image, ImageDraw, ImageFont, ImageOps
from numpy import linalg
from numpy import matrix
import pdb
import pandas as pd
import copy
from typing import Dict, List, Any, Union

def dir_path(dname):
    '''
    If the directory doesn't exist then make it.
    '''
    try:
        os.makedirs(dname)
    except os.error:
        pass
    return dname


class RenderScenes(object):

    def __init__(self, opts):
        self.opts = opts
        self.prev_scene_config_file = ''

    def run(self):
        if (self.opts['--render']):
            self.render_scenes(True)
        else:
            self.render_scenes(False)

    def render_scenes(self, render=True):

        # ---------- READ OPTIONS ----------
        # E.g. './data/stories/0001/scene.json'
        json_data = self.opts['<jsondata>']
        self.render = render
        if (self.opts['--outdir'] == 'USE_DEF'):
            if path.isdir(json_data):
                # If path is of the form './data/stories/'
                self.render_dir = './data/image_renderings/'
            else:
                # if path is of the form './data/stories/0001/scene.json'
                self.render_dir = path.join('./data/image_renderings/', path.split(path.split(path.normpath(json_data))[0])[1])
        else:
            self.render_dir = self.opts['--outdir']
        dir_path(self.render_dir)
        
        if self.opts['--previewdir'] == 'USE_DEF':
            self.preview_dir = './data/previews/'
        else:
            self.preview_dir = self.opts['--previewdir']
        dir_path(self.preview_dir)
            
        self.clipart_img_format = self.opts['--format']
        
        self.overwrite = self.opts['--overwrite']
        
        self.preview = self.opts['--preview']

        if (self.opts['--cliparts_dir'] == 'USE_DEF'):
            self.base_url_interface = './data/cliparts/'
        else:
            self.base_url_interface = self.opts['--site_pngs_dir']

        if (self.opts['--config_dir'] == 'USE_DEF'):
            self.config_folder = './data/scene_config_files/'
        else:
            self.config_folder = self.opts['--config_dir']

        # ---------- ------------- ----------

        self.artificial_z_vals = 6

        # start the rendering process
        # If path is a directory, it is expected to contain folders with storyIDs that in-turn contain scene.json files
        if path.isdir(json_data):
            for dirname in os.listdir(json_data):
                if path.isdir(path.join(json_data, dirname)):
                    curdir = path.join(json_data, dirname)
                    outdir = path.join(self.render_dir, dirname)
                    dir_path(curdir)
                    dir_path(outdir)
                    rendered_data = self.render_dir_of_scenes(curdir, outdir)
                    if not rendered_data:
                        print('Scene not rendered for dir: {}'.format(curdir))
                        continue
                    else:
                        if self.preview:
                            rendered_data = self.create_preview(outdir, rendered_data)
                            print('processed {}'.format(dirname))
        # Else path should directly point to a scene.json file
        else:
            curdir = path.split(path.normpath(json_data))[0]
            outdir = self.render_dir
            rendered_data = self.render_dir_of_scenes(curdir, outdir)
            if not rendered_data:
                print('Scene not rendered for dir: {}'.format(curdir))
            else:
                if self.preview:
                    rendered_data = self.create_preview(outdir, rendered_data)
        return True

    def text_wrap(self, text, font, max_width):
        """Wrap text base on specified width.
        This is to enable text of width more than the image width to be display
        nicely.
        @params:
            text: str
                text to wrap
            font: obj
                font of the text
            max_width: int
                width to split the text with
        @return
            lines: list[str]
                list of sub-strings
        """
        lines = []

        # If the text width is smaller than the image width, then no need to split
        # just add it to the line list and return
        if font.getsize(text)[0] <= max_width:
            lines.append(text)
        else:
            # split the line by spaces to get words
            words = text.split(' ')
            i = 0
            # append every word to a line while its width is shorter than the image width
            while i < len(words):
                line = ''
                while i < len(words) and font.getsize(line + words[i])[0] <= max_width:
                    line = line + words[i] + " "
                    i += 1
                if not line:
                    line = words[i]
                    i += 1
                lines.append(line)
        return ' \n'.join(lines)

    def create_preview(self, outdir, details):
        # get details relevant to the current story for preview generation
        title = details['title']
        theme = '; '.join(details['theme'])
        imgnames = details['panels']
        story = details['story']
        imgdir = path.split(imgnames[0])[0]
        outdir = path.join(self.preview_dir, details['storyid'])
        dir_path(outdir)

        if self.opts['--istext']:
            if len(title) == 0:
                title = 'N/A'
            if len(theme) == 0:
                theme = 'N/A'
            totaltext = '{} \nTheme: {}'.format(title.upper(), theme.title())
            totaltext += ' \n '
        imgsize = (350, 200)
        offset = 20
#         max_num_lines = 0
#         fnt = ImageFont.truetype('/Library/Fonts/Arial Unicode.ttf', 20)
#         for idx in range(len(story)):
#             curtext = story[idx]
#             lines = self.text_wrap(curtext, fnt, imgsize[0] - 5)
#             num_lines = lines.count('\n')
#             if num_lines > max_num_lines:
#                 max_num_lines = num_lines
        if self.opts['--istext']:
            #totalheight = int(imgsize[1] * (1.5 + math.ceil(max_num_lines/5)))
            totalheight = int(imgsize[1] * 4.5)
        else:
            totalheight = imgsize[1] + (offset * 2)
        totalwidth = (imgsize[0] * len(imgnames)) + (offset * len(imgnames))
        final_img = Image.new('RGB', (totalwidth, totalheight), color='white')
        width_offset = 0
        height_offset = offset * 4
        if self.opts['--istext']:
            # fnt = ImageFont.truetype('/Library/Fonts/arial.ttf', 20)
            fnt = ImageFont.truetype('/Library/Fonts/Arial Unicode.ttf', 20)
            temptext = Image.new('RGB', (totalwidth, height_offset), color='white')
            d = ImageDraw.Draw(temptext)
            d.text((5, 5), totaltext, font=fnt, fill=(0, 0, 0))
            final_img.paste(temptext, (width_offset, 0))
        for idxs in range(len(imgnames)):
            idx = idxs
            tempimg = Image.open(imgnames[idx])
            tempimg.thumbnail(imgsize, Image.ANTIALIAS)
            if self.opts['--istext']:
                final_img.paste(tempimg, (width_offset, height_offset))
            else:
                final_img.paste(tempimg, (width_offset, offset))
            if self.opts['--istext']:
                curtext = story[idx]
                temptext = Image.new('RGB', (imgsize[0], int(imgsize[1]*1.5)), color='white')
                d = ImageDraw.Draw(temptext)
                lines = self.text_wrap(curtext, fnt, imgsize[0] - 5)
                d.text((5, 5), lines, font=fnt, fill=(0, 0, 0))
                final_img.paste(temptext, (width_offset, imgsize[1] + height_offset + 20))
            width_offset += (tempimg.size[0] + offset)
        final_img = ImageOps.invert(final_img)
        bbox = final_img.getbbox()
        final_img = final_img.crop((0, 0, totalwidth, bbox[-1]+20))
        final_img = ImageOps.invert(final_img)
        final_img.save(path.join(outdir, 'preview.jpg'), self.clipart_img_format, quality='web_high')

        return True

    def render_dir_of_scenes(self, curdir, outdir):

        storyid = path.split(curdir)[1]
        if not path.isfile(path.join(
                curdir, 'scene.json')):
            return False

        # load jsons
        try:
            scene = json.load(open(path.join(curdir, 'scene.json')))
            meta = json.load(open(path.join(curdir, 'meta.json')))
        except UnicodeDecodeError:
            print('not a valid submission: {}'.format(curdir))
            return False

        # render the panels
        imgnames = []
        for panelnum in range(len(scene)):
            cur_bg = meta['bg'][panelnum]
            cur_scene = scene[panelnum]
            if self.render:
                imgname = self.render_one_scene(cur_scene, outdir, cur_bg,
                                                '{}'.format(panelnum))
            else:
                img_name = '{}_{}.png'.format('panel', panelnum)
                imgname = '/'.join([outdir, img_name])
            imgnames.append(imgname)

        # compile all data into dict and put it inside allfiles
        curdict = dict()
        curdict['panels'] = imgnames
        curdict['story'] = meta['story']
        curdict['title'] = meta['title']
        curdict['theme'] = meta['theme']
        curdict['storyid'] = storyid
        return curdict

    def render_one_scene(self, data, outdir, bg, panelnum):

        img_name = '{}_{}.jpg'.format('panel', panelnum)
        img_file = '/'.join([outdir, img_name])

        # Skip if already exists and no overwrite flag
        if not os.path.isfile(img_file) or self.overwrite is True:
            try:
                cur_scene = data['scene']
            except KeyError:
                cur_scene = data
            self.read_scene_config_file(cur_scene['sceneConfigFile'])
            cur_scene_type = cur_scene['sceneType']
            cur_scene_config = self.scene_config_data[cur_scene_type]
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

            if bg is not None:
                bgImg = 'BG{}.png'.format(bg)
            else:
                bgImg = cur_scene_config['bgImg']
            bg_img_file = os.path.join(self.base_url_interface,
                                       cur_scene_config['baseDir'],
                                       bgImg)
            bg_img = Image.open(bg_img_file)

            # depth is corrected to include artificial values for overlapping objects
            # take care of that
            #num_artificial_z_size = (num_z_size * self.artificial_z_vals) + num_z_size
            # // Make sure we get the depth ordering correct
            # (render the objects using their depth order)
            # (num_depth0-1, num_depth0-2, ... 0)
            for k in reversed(range(0, num_depth0)):
                #     if (curDepth0Used[k] <= 0)
                #           { // not used, just to accelerate the process
                #         continue;
                #           }
                for j in reversed(range(0, num_z_size + 1)):
                    # // for people, choose both the expression and the pose
                    for L in reversed(range(0, num_depth1)):
                        # if (curDepth1Used[l] <= 0)
                        #     { // not used, just to accelerate the process
                        #       continue;
                        #      }
                        for i in range(0, len(cur_avail_obj)):
                            if (cur_avail_obj[i]['instance'][0]['depth0'] == k):
                                for m in range(0, cur_avail_obj[i]['numInstance']):
                                    cur_obj = copy.deepcopy(cur_avail_obj[i]['instance'][m])
                                    if (cur_obj['present'] is True and
                                        cur_obj['z'] == j and
                                        cur_obj['depth1'] == L):
                                        # cur_obj['z'] = cur_obj['z'] // self.artificial_z_vals
                                        if (cur_obj['type'] == 'human'):
                                            if (cur_obj['deformable'] is True):
                                                self.overlay_deformable_person(
                                                        bg_img, img_pad_num,
                                                        cur_obj, cur_z_scale)
                                            else:
                                                self.overlay_nondeformable_person(
                                                        bg_img, img_pad_num,
                                                        cur_obj, cur_z_scale)
                                        else:
                                            self.overlay_nondeformable_obj(
                                                    bg_img, img_pad_num,
                                                    cur_obj, cur_z_scale)

            bg_img = bg_img.convert('RGB')
            bg_img.save(img_file, self.clipart_img_format, quality='web_high')
        return img_file

    def read_scene_config_file(self, scene_config_filename):

        scene_config_file = os.path.join(self.config_folder,
                                         scene_config_filename)

        # Only need to load if not the same as previous
        if (scene_config_file != self.prev_scene_config_file):

            self.prev_scene_config_file = scene_config_file

            with open(scene_config_file) as json_fileid:
                self.scene_config_data = json.load(json_fileid)

                obj_filenames = self.scene_config_data['clipartObjJSONFile']
                object_data = {}
                for obj_file in obj_filenames:
                    obj_file_vers = obj_file['file']
                    for obj_dtype, obj_type_file in obj_file_vers.items():
                        with open(os.path.join(self.config_folder,
                                               obj_type_file)) as f:
                            obj = json.load(f)
                            if obj['objectType'] not in object_data:
                                object_data[obj['objectType']] = {}
                            object_data[obj['objectType']][obj_dtype] = obj
                self.object_data = object_data

    def get_object_attr_types(self, obj_type, deform_type):

        cur_attr_types = []

        for cur_attr_name in self.object_data[obj_type][deform_type][
                'attributeTypeList']:
            cur_attr_type = {}

            if (cur_attr_name == 'Type'):
                cur_attr_type = {'num': 'numType', 'id': 'typeID'}
            elif (cur_attr_name == 'Pose'):
                cur_attr_type = {'num': 'numPose', 'id': 'poseID'}
            elif (cur_attr_name == 'Expression'):
                cur_attr_type = {'num': 'numExpression', 'id': 'expressionID'}

            cur_attr_types.append(cur_attr_type)

        return cur_attr_types

    def obj_img_filename(self, img_pad_num, obj, attr1=None, attr2=None,
                         attr3=None):

        object_data = self.object_data
        # TODO Don't hardcode this?
        clipart_img_format = 'png'

        cur_obj_type = obj['type']
        cur_obj_name = obj['name']
        if (obj['deformable'] is True):
            cur_obj_deform = 'deformable'
        else:
            cur_obj_deform = 'nondeformable'

        cur_attr_types = self.get_object_attr_types(
                cur_obj_type, cur_obj_deform)

        if (attr1 is None):
            attr1 = obj[cur_attr_types[0]['id']]

        if (cur_obj_type == 'largeObject' or cur_obj_type == 'smallObject'):
            sceneFolder = self.scene_config_data['baseDirectory'][
                    obj['baseDir']]

            name = '{0}{1}.{2}'.format(cur_obj_name,
                                       str(attr1+1).zfill(img_pad_num),
                                       clipart_img_format)
            filename = os.path.join(self.base_url_interface, sceneFolder, name)
        elif (cur_obj_type == 'animal'):
            animalFolder = object_data['animal'][cur_obj_deform][
                    'baseDirectory']
            if cur_obj_name == 'Bee':
                attr1 = 0
            name = '{0}{1}.{2}'.format(cur_obj_name,
                                       str(attr1 + 1).zfill(img_pad_num),
                                       clipart_img_format)
            filename = os.path.join(self.base_url_interface, animalFolder,
                                    name)
        elif (cur_obj_type == 'human'):

            if (attr2 is None):
                attr2 = obj[cur_attr_types[1]['id']]

            if (attr3 is None):
                attr3 = obj['styleID']

            humanFolder = object_data['human'][cur_obj_deform]['baseDirectory']
            styleFolder = '{0}{1}'.format(cur_obj_name,
                                          str(attr3 + 1).zfill(img_pad_num))

            name = '{0}{1}.{2}'.format(str(attr2 + 1).zfill(img_pad_num),
                                       str(attr1 + 1).zfill(img_pad_num),
                                       clipart_img_format)
            filename = os.path.join(self.base_url_interface, humanFolder,
                                    styleFolder, name)
        else:
            filename = None

        return filename

    # Needed for the interface but not here (loads just the heads w/ expr)
    # TODO Update to support this class
    def obj_expr_filename(self, img_pad_num, obj):
        filename = None
        clipart_img_format = 'png'

        cur_obj_type = obj['type']
        cur_obj_name = obj['name']
        if (obj['deformable'] is True):
            obj_deform = 'deformable'
        else:
            obj_deform = 'nondeformable'

        if (cur_obj_type == 'human'):
            humanFolder = self.object_data['human'][obj_deform][
                    'baseDirectory']
            name = '{0}{1}.{2}'.format(cur_obj_name,
                                       str(obj['expressionID'] + 1).zfill(
                                               img_pad_num),
                                       clipart_img_format)
            filename = os.path.join(self.base_url_interface, humanFolder,
                                    'Expressions', name)

        return filename

    def paperdoll_part_img_filename_expr(self, obj, part_name):

        filename = None
        cur_obj_type = obj['type']
        cur_obj_name = obj['name']

        if (obj['deformable'] is True):
            obj_deform = 'deformable'
        else:
            obj_deform = 'nondeformable'

        clipart_img_format = 'png'

        if (cur_obj_type == 'human'):
            humanFolder = self.object_data['human'][obj_deform][
                    'baseDirectory']
            name = '{0}.{1}'.format(part_name, clipart_img_format)
            filename = os.path.join(self.base_url_interface, humanFolder,
                                    cur_obj_name, name)

        return filename

    def get_render_transform(self, X1, X, rad, flip, scale):

        if (flip == 0):
            S = matrix([[scale, 0, 0],
                        [0, scale, 0],
                        [0, 0, 1]])
            T1 = matrix([[1, 0, X1[0]],
                        [0, 1, X1[1]],
                        [0, 0, 1]])
            T2 = matrix([[1, 0, X[0]],
                        [0, 1, X[1]],
                        [0, 0, 1]])
            R = matrix([[math.cos(rad), -math.sin(rad), 0],
                        [math.sin(rad), math.cos(rad), 0],
                        [0, 0, 1]])
            T = S*T2*R*T1
        else:  # (flip == 1)
            rad *= -1
            S = matrix([[scale, 0, 0],
                        [0, scale, 0],
                        [0, 0, 1]])
            T1 = matrix([[1, 0, X1[0]],
                        [0, 1, X1[1]],
                        [0, 0, 1]])
            T2 = matrix([[1, 0, -X[0]],
                        [0, 1, X[1]],
                        [0, 0, 1]])
            R = matrix([[math.cos(rad), -math.sin(rad), 0],
                        [math.sin(rad), math.cos(rad), 0],
                        [0, 0, 1]])
            F = matrix([[-1, 0, 0],
                        [0, 1, 0],
                        [0, 0, 1]])
            T = F*S*T2*R*T1

        Tinv = linalg.inv(T)
        Tinvtuple = (Tinv[0, 0], Tinv[0, 1], Tinv[0, 2],
                     Tinv[1, 0], Tinv[1, 1], Tinv[1, 2])

        return Tinvtuple

    def overlay_deformable_person(self, bg_img, img_pad_num, cur_obj, z_scale):

        num_parts = len(cur_obj['body'])
        scale = cur_obj['globalScale'] * z_scale[cur_obj['z']]

        bg_size = bg_img.size
        flip = cur_obj['flip']
        for partIdx in range(0, num_parts):
            part = cur_obj['body'][partIdx]
            part_name = part['part']
            X1 = [-part['childX'],
                  -part['childY']]
            #pose = 0
            #X = [cur_obj['deformableX-mod-{}'.format(pose)][partIdx],
            #     cur_obj['deformableY-mod-{}'.format(pose)][partIdx]]
            #rotation = cur_obj['deformableGlobalRot-mod-{}'.format(pose)][partIdx]

            X = [cur_obj['deformableX'][partIdx],
                 cur_obj['deformableY'][partIdx]]
            rotation = cur_obj['deformableGlobalRot'][partIdx]

            Tinvtuple = self.get_render_transform(X1, X,
                                                  rotation, flip, scale)
            if (part_name == 'Head'):
                part_fn = self.obj_expr_filename(img_pad_num, cur_obj)
            else:
                part_fn = self.paperdoll_part_img_filename_expr(
                        cur_obj, part_name)

            # TODO Update so don't keep opening files for efficiency
            part_img = Image.open(part_fn)
            part_tf = part_img.transform(bg_size, Image.AFFINE,
                                         Tinvtuple, resample=Image.BICUBIC)

            bg_img.paste(part_tf, (0, 0), part_tf)
        return bg_img


    def overlay_nondeformable_person(self, bg_img, img_pad_num,
                                     cur_obj, z_scale):
        # In our case, we're just computing the filename and loading it, so
        # a nondeformable person is the same as nondeformable objects.
        self.overlay_nondeformable_obj(bg_img, img_pad_num, cur_obj, z_scale)

    def index2grid_coord(self, index):
        return index % 128, index // 128

    def coord2index(self, coord):
        col_idx = int(float(coord[0] - 1) / 5.496062992125984 + 0.5)
        row_idx = int(float(coord[1] - 1) / 3.1338582677165356 + 0.5)
        col_idx = max(0, min(col_idx, 128 - 1))
        row_idx = max(0, min(row_idx, 128 - 1))
        return row_idx * 128 + col_idx

    def overlay_nondeformable_obj(self, bg_img, img_pad_num, cur_obj, z_scale):

        scale = z_scale[cur_obj['z']]

        # TODO We should just load all possible
        # clipart images once and then index into them
        # with filename for efficiency
        cur_filename = self.obj_img_filename(img_pad_num, cur_obj)
        cur_clipart_img = Image.open(cur_filename)

        (w, h) = cur_clipart_img.size
        X = [cur_obj['x'], cur_obj['y']]
        colOffset = -w / 2.0
        rowOffset = -h / 2.0
        colOffset *= scale
        rowOffset *= scale

        X[0] += colOffset
        X[1] += rowOffset

        offset = (int(X[0]), int(X[1]))
        resized = cur_clipart_img.resize((int(w*scale), int(h*scale)),
                                         Image.ANTIALIAS)

        if (cur_obj['flip'] == 0):
            bg_img.paste(resized, offset, resized)
        else:
            flipped = resized.transpose(Image.FLIP_LEFT_RIGHT)
            bg_img.paste(flipped, offset, flipped)
        return bg_img


def main():
    '''
    Usage:
        render_scenes_json.py <jsondata>
        [--render --outdir=OD --previewdir=PD --preview --overwrite --istext --cliparts_dir=ID --config_dir=CD --format=FMT]

    Options:
        <jsondata>          Either a filepath to a scene.json file PREFERABLY within a folder named with storyID or a directory of folders with multiple storyID directories
                            For example: ./data/stories/0001/scene.json or ./data/stories
        --render            True if you want to render each of the three images per story
        --outdir=OD         Directory to put the processed rendered pngs [default: USE_DEF]
        --previewdir=PD     Dir to put the previews generated [default: USE_DEF]
        --format=FMT        Image file format [default: jpeg]
        --cliparts_dir=ID   Path to the site_pngs dir (contains all object images) [default: USE_DEF]
        --config_dir=CD     Path to the config data files (contains all object data) [default: USE_DEF]
        --overwrite         Overwrite files even if they exist
        --preview           Create previews
        --istext            Does preview require text as well
    '''

    # USE_DEF for --cliparts_dir is ./data/cliparts/
    # USE_DEF for --config_dir is ./data/scene_config_files/
    # USE_DEF for --outdir is ./data/image_renderings/{story_id}

    # 1. set up command line interface
    import docopt
    import textwrap
    main_args = docopt.docopt(textwrap.dedent(main.__doc__))

    print('')
    print(main_args)
    print('')

    rend = RenderScenes(main_args)
    rend.run()


if __name__ == '__main__':
    main()

