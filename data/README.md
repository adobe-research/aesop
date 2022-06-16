# AESOP: Abstract Encoding of Stories, Objects and Pictures (ICCV 2021)
[Hareesh Ravi](https://hareesh-ravi.github.io/) | [Kushal Kafle](https://kushalkafle.com/) | [Scott Cohen](https://research.adobe.com/person/scott-cohen/) | [Jonathan Brandt](https://research.adobe.com/person/jonathan-brandt/) | [Mubbasir Kapadia](https://ivi.cs.rutgers.edu/) <br>

This is the official repository for our ICCV 2021 paper "AESOP: Abstract Encoding of Stories, Objects and Pictures". <br> 

---

## DATA

The data necessary for this repo are found in `data.zip` and are organized as follows
- `./data/stories/` is a directory of folders with two json files in each folder. 
    - `scene.json` is a list of 3 dictionaries in a specific format from [Abstract Scenes](https://github.com/GT-Vision-Lab/abstract_scenes_v002) dataset. Each dictionary contains parameters to render 1 image in the story. This is the input to `renderer.py`. For ease of use to train models, use `train|test.json` files that has only parameters that are necessary to train a model or predict from a model.
    - `meta.json` has the `title`, `genre/theme`, `story` and `bg` where `bg` tells which background is used in the image.
- `./data/cliparts/` has all the separate clipart images that are used to compose an image (not to be disturbed/changed).
- `./data/scene_config_files/` has config files necessary to render image from scene.json files (DO NOT EDIT)
- `./data/objects.json` gives a mapping between clipart objects and indices
- `./data/character_names.json` gives mapping between person names used in stories such as 'Mike' and 'Emily' to their names in scene.json.


#### RENDERING PREVIEWS

For ease of viewing, we also provide the pre-rendered previews in `previews.tar.gz` in the release tab which contains:

- `previews/image_renderings/` has all folders with same storyIDs but 3 images inside each folder corresponding to 3 panels in each story.
- `previews/previews/` has images that shows the entire story with 3 images, 3 text, title and theme.


## TRAINING DATA

If representing image as a set/sequence of objects and attributes as described in our paper and for general ease of use, leverage the train and test json files that have all necessary data from scene.json and meta.json. The 'scene.json' and 'meta.json' files are too noisy and are in that format to support the renderer.py.
- `./data/train.json`
- `./data/test.json` 

The jsons contain a list of dictionaries like,

```
[storydict_1, storydict_2, ..., storydict_n]
```

where, 

```
storydict_1 = 
  {
    storyid    = storyid 
    theme      = list of human annotated genres
    title      = title provided by person that wrote the story
    split      = 'train' or 'test'
    image_data = list of dictionaries with data for each image, e.g., [image_1_dict, image_2_dict, image_3_dict]
    text       = list of story text, e.g., ['text_1', 'text_2', 'text_3']
    bg         = list of backgrounds used, e.g., [bg_1, bg_2, bg_3]
    image_path = list of paths to images, e.g., ['path_to_image_1', 'path_to_image_2', 'path_to_image_3']
    scenetype  = 'Extended_All'
  }
```

where `image_i_dict = [obj_1_dict, ocj_2_dict, ..., ocj_n_dict]`, is a list of object_dictionaries with data about all objects present in that image. Some of these data are the important ones that need to be predicted or modelled. i.e. these attributes once predicted by the model can be given to `utils.py --dict2scene`. These attributes are, 
```
  {
     idx          = index corresponding to that object and its type,
     x            = x position of center of that clipart object in the image,
     y            = y position of center of that clipart object in the image,
     depth        = z value according to scene_config,
     flip         = 0 or 1 based on whether object is facing left or right,
     pose         = pose value if object is animal and rotation values if object is human and none otherwise.
     expression   = None if non-human or 0-9 value for humans,
  }
```
The `idx` can be used as it is or you can define your own hierarchy of objects or use them as just words or the cliparts directly for visual input etc. We treate all objects and their types as separate objects and assign an index to each of those.

Additionaly, the object dict contains some attributes that are standard or is not required to be predicted (unless formulated otherwise) such as,

```
  {
     name         = name of the object (can be obtained from ./data/objects.json using idx),
     type_name    = combining name and type as name--type (can be obtained from ./data/objects.json using idx),
     objclass     = animal, human, small or large object (can be obtained from ./data/objects.json using idx),
     depth0       = constant for this object defined according to scene_config,
     depth1       = constant for this object defined according to scene_config, 
  }
```

## INSTRUCTIONS

To replicate the problem formulations and modelling techniques in the paper, here is the general flow of things:

- Use `train|test.json` files to train a model to predict necessary attributes (as described above using your own model) depending on the problem formulation. 
- Once predicted, put the predictions in the same dict format as above (as dict using your own code)
- Then convert this to `scene.json` and `meta.json` (using instructions in CODE readme in homepage of this repo)
- Then render the predictions using `renderer.py` (using instructions in CODE readme in homepage of this repo)
