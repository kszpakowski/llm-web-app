FROM node:latest as frontend-builder

WORKDIR /code

COPY ./frontend/package*.json ./

RUN npm install

COPY ./frontend/public ./public
COPY ./frontend/src ./src
COPY ./frontend/.eslintrc.json  ./frontend/next.config.js ./frontend/postcss.config.js ./frontend/tailwind.config.ts ./frontend/tsconfig.json ./

RUN npm run build

FROM python:3.9

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app

COPY --from=frontend-builder /code/out ./static

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
