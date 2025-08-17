<script setup>
import 'material-icons/iconfont/material-icons.css';
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <header>
    <nav class="navbar navbar-expand-lg p-auto px-4 pt-1 pb-0 border-bottom">
      <div class="container justify-content-start mx-0">
        <RouterLink id="logo" to="/" class="navbar-brand white fs-1"><h1>ShashGuru</h1></RouterLink>
        <div class="navbar-nav ms-5">
          <RouterLink to="/" class="nav-link mx-3"><span class="fs-4">HOME</span></RouterLink>
          <RouterLink to="/live" class="nav-link mx-3"><span class="fs-4">LIVE</span></RouterLink>
          <RouterLink to="/about" class="nav-link mx-3"><span class="fs-4">ABOUT</span></RouterLink>
        </div>
      </div>
    </nav>
  </header>

  <RouterView />
</template>

<style scoped>

nav  {
  border-color: #aaa23a !important;
  background: #232323 !important;
}
a {
  color: #e6e6b3;
  transition: color 0.2s;
}
a:hover {
  color: #cdd26a;
}
a:focus {
  color: #cdd26a;
  font-weight: bolder;
}
#logo {
  font-weight: 900;
  color: #cdd26a;
  letter-spacing: 2px;
  text-shadow: 1px 1px 4px #232323;
}


header h1 {
  color: #cdd26a;
  text-shadow: 1px 1px 6px #232323;
}


</style>

<style>
/* Custom palette rules */
.custom-bg-primary {
  background: #aaa23a ;
}
</style>