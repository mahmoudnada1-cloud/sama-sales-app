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
# --- add engine logo header (logo cropped from the original screenshot) ---
from PIL import ImageFont
FT=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',40)
def header(src,logo_box,name,content,out):
    lg=Image.open(I+src).convert('RGB').crop(logo_box)
    h=72; lg=lg.resize((int(lg.width*h/lg.height),h),Image.LANCZOS)
    c=Image.open(content); H=110
    im=Image.new('RGB',(c.width,c.height+H),lg.getpixel((1,1)))
    im.paste(lg,(28,(H-h)//2)); d=ImageDraw.Draw(im)
    d.text((28+lg.width+18,H//2),name,font=FT,fill=(20,20,20),anchor='lm')
    d.line((0,H-1,c.width,H-1),fill=(225,225,225),width=2)
    im.paste(c,(0,H)); im.save(out)
header('34.webp',(10,10,54,54),'ChatGPT','work/chatgpt.png','work/chatgpt.png')
header('35.png',(12,18,72,78),'Perplexity','work/perplexity.png','work/perplexity.png')
header('36.png',(16,6,54,44),'Gemini','work/gemini.png','work/gemini.png')
