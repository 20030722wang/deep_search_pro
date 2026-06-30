# ============================================================
# 前端构建阶段 - Vue 3 + Vite
# ============================================================
FROM node:22-alpine AS build

WORKDIR /app

# 安装依赖
COPY package.json package-lock.json ./
RUN npm ci

# 构建
COPY . .
RUN npm run build

# ============================================================
# 生产运行阶段 - Nginx
# ============================================================
FROM nginx:alpine

# 复制构建产物
COPY --from=build /app/dist /usr/share/nginx/html

# 复制 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
