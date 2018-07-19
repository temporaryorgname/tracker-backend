import torch
import torchvision
import torchvision.models as models
from PIL import Image
import numpy as np

food_classes = {
    440: 'beer bottle',
    441: 'beer glass',
    504: 'coffee mug',
    505: 'coffeepot',
    509: 'confectionery, confectionary, candy store',
    599: 'honeycomb',
    737: 'pop bottle, soda bottle',
    898: 'water bottle',
    899: 'water jug',
    901: 'whiskey jug',
    907: 'wine bottle',
    924: 'guacamole',
    928: 'ice cream, icecream',
    929: 'ice lolly, lolly, lollipop, popsicle',
    930: 'French loaf',
    931: 'bagel, beigel',
    932: 'pretzel',
    933: 'cheeseburger',
    934: 'hotdog, hot dog, red hot',
    935: 'mashed potato',
    936: 'head cabbage',
    937: 'broccoli',
    938: 'cauliflower',
    939: 'zucchini, courgette',
    940: 'spaghetti squash',
    941: 'acorn squash',
    942: 'butternut squash',
    943: 'cucumber, cuke',
    944: 'artichoke, globe artichoke',
    945: 'bell pepper',
    946: 'cardoon',
    947: 'mushroom',
    948: 'Granny Smith',
    949: 'strawberry',
    950: 'orange',
    951: 'lemon',
    952: 'fig',
    953: 'pineapple, ananas',
    954: 'banana',
    955: 'jackfruit, jak, jack',
    956: 'custard apple',
    957: 'pomegranate',
    959: 'carbonara',
    960: 'chocolate sauce, chocolate syrup',
    961: 'dough',
    962: 'meat loaf, meatloaf',
    963: 'pizza, pizza pie',
    964: 'potpie',
    965: 'burrito',
    966: 'red wine',
    967: 'espresso',
    968: 'cup',
    969: 'eggnog',
    987: 'corn'
}

#inception = models.inception_v3(pretrained=True)
resnet = models.resnet18(pretrained=True)
resnet.eval()

n = 299
n = 224
#file_name = '/home/howardh/data/uploads/Cat03.jpg'
#file_name = '/home/howardh/data/uploads/875806_R.jpg'
file_name = '/home/howardh/data/uploads/Eq_it-na_pizza-margherita_sep2005_sml.jpg'
img = Image.open(file_name)
img = img.resize((n,n))
img = np.array(img)/255
normalize = torchvision.transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
img = normalize(torch.from_numpy(img))
img = img.permute([2,0,1]).view(-1,3,n,n).float()
#x = inception(torch.cat([img,img],dim=0))
x = resnet(img)
scores = x[0].detach().numpy()
indices = np.argsort(scores) # Descending order, so look at the last entry
top_5 = indices[-5:]

for i in top_5:
    if i in food_classes:
        print(food_classes[i])
        break
else:
    print('None found')

# See https://discuss.pytorch.org/t/pretrained-resnet-constant-output/2760/8
