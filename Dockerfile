FROM python:3.7-alpine

LABEL maintainer="Chase McManning <cmcmanning@gmail.com>"

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt

# build-deps are packages required for building zeroc-ice
RUN apk add --no-cache \
    libstdc++ \
    make \
    gcc \
    g++ \
    python3-dev \
    py3-setuptools \
    openssl-dev \
    bzip2-dev \
    # Pillow prereqs
    tiff-dev jpeg-dev openjpeg-dev zlib-dev freetype-dev lcms2-dev \
    libwebp-dev tcl-dev tk-dev harfbuzz-dev fribidi-dev libimagequant-dev \
    libxcb-dev libpng-dev \
    && pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 5000
CMD ["python", "/app/entry.py"]
