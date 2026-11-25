from PIL import Image, ImageFilter, ImageDraw
I='/tmp/claude-0/-home-user-sama-sales-app/26437c45-bc14-5474-afd5-08d367324369/images/'
OR=(204,85,0)
def blur(im,box,r=14):
    reg=im.crop(box).filter(ImageFilter.GaussianBlur(r)); im.paste(reg,box)
def pill(im,box):
    x0,y0,x1,y1=box; blur(im,(x0-6,y0-4,x1+6,y1+4),11)
# ChatGPT
a=Image.open(I+'34.webp').convert('RGB')
pill(a,(728,312,862,350))
a.crop((400,95,1590,770)).save('work/chatgpt.png')
# Perplexity
b=Image.open(I+'35.png').convert('RGB')
pill(b,(620,288,742,324))
for box in [(556,522,820,560),(458,578,820,650)]: pill(b,box)
b.crop((400,125,1345,662)).save('work/perplexity.png')
# Gemini
c=Image.open(I+'36.png').convert('RGB')
for box in [(500,68,1499,170),(500,180,1499,250),(500,372,1499,445),(500,495,1499,700)]: blur(c,box,16)
for box in [(632,266,748,298),(1330,298,1418,330),(1036,298,1142,330),(800,298,906,330),(636,298,792,330)]: pill(c,box)
c.crop((500,15,1499,700)).save('work/gemini.png')
