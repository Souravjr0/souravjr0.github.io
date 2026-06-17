# Decoder tool for clack's messages
mapping = {
    'q': 'th', 'w': 'c', 'e': 'y', 'r': 'k', 't': 'e', 'y': 'h', 'u': 'g', 'i': 'w', 'o': 'w', 'p': 'z',
    '[': 'x', ']': 'b', 'a': 'f', 's': 's', 'd': 'v', 'f': 'a', 'g': 'n', 'h': 'p', 'j': 'o', 'k': 'l',
    'l': 'd', ';': 'w', "'": 'e', 'z': 'i', 'x': 'h', 'c': 'c', 'v': 'm', 'b': 'i', 'n': 't', 'm': 'b',
    ',': 'b', '.': 'y'
}

# Wait, the instruction says:
# "cook45 decodes character-by-character according to the table:
# q=th w=c e=y r=k t=e y=h u=g i=w o=w p=z [=x ]=b a=f s=s d=v f=a g=n h=p j=o k=l l=d ;=w '=e z=i x=h c=c v=m b=i n=t m=b ,=b .=y"

text = "Check clack, how compicated this was, i had given this to claude clack and he has been does a turn into the pump.fum and help me towards this, asked you and you ingored me."

# Let's write a script to decode this and other combinations of words.
# Wait, let's decode character by character:
def decode(char):
    is_upper = char.isupper()
    c = char.lower()
    if c in mapping:
        decoded = mapping[c]
        if is_upper:
            return decoded.capitalize()
        return decoded
    return char

decoded_text = "".join(decode(c) for c in text)
print("Decoded:")
print(decoded_text)
