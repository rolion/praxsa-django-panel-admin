// Sidebar route metadata
export interface RouteInfo {
  path: string;
  title: string;
  iconType: string;
  icon: string;
  class: string;
  groupTitle: boolean;
  badge: string;
  badgeClass: string;
  /** Permiso Django (codename del app product) requerido para ver el item. Solo UX: la barrera
   * real es el permiso del endpoint (ver ADR-reportes-utilidad-ventas-diarias-permisos). */
  permission?: string;
  submenu: RouteInfo[];
}

/** Oculta los items cuyo permiso no cumple el usuario y los grupos que se quedan sin
 * submenus. Los items sin `permission` se muestran siempre. */
export function filterByPermission(
  items: RouteInfo[],
  hasPermission: (codename: string) => boolean
): RouteInfo[] {
  const visibles: RouteInfo[] = [];
  for (const item of items) {
    if (item.permission && !hasPermission(item.permission)) {
      continue;
    }
    const submenu = item.submenu ?? [];
    const submenuVisible = filterByPermission(submenu, hasPermission);
    if (submenu.length > 0 && submenuVisible.length === 0) {
      continue;
    }
    visibles.push({ ...item, submenu: submenuVisible });
  }
  return visibles;
}
