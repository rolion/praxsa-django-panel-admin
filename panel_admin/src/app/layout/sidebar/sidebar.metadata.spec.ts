import { RouteInfo, filterByPermission } from './sidebar.metadata';

const item = (title: string, overrides: Partial<RouteInfo> = {}): RouteInfo => ({
  path: `/${title}`, title, iconType: '', icon: '', class: '', groupTitle: false, badge: '', badgeClass: '',
  submenu: [], ...overrides,
});

describe('filterByPermission', () => {
  const menu: RouteInfo[] = [
    item('Inicio'),
    item('Reportes', {
      submenu: [
        item('Ventas Diarias', { permission: 'view_proxy_pagos' }),
        item('Utilidad', { permission: 'view_utilidades' }),
      ],
    }),
    item('Vacio', { submenu: [] }),
  ];
  const titles = (items: RouteInfo[]) => items.map((i) => i.title);

  it('muestra siempre los items sin permiso, incluso grupos sin submenus', () => {
    expect(titles(filterByPermission(menu, () => false))).toEqual(['Inicio', 'Vacio']);
  });

  it('Admin ve ambos reportes', () => {
    const result = filterByPermission(menu, () => true);
    expect(titles(result)).toEqual(['Inicio', 'Reportes', 'Vacio']);
    expect(titles(result[1].submenu)).toEqual(['Ventas Diarias', 'Utilidad']);
  });

  it('Caja ve solo Ventas Diarias', () => {
    const result = filterByPermission(menu, (codename) => codename === 'view_proxy_pagos');
    expect(titles(result[1].submenu)).toEqual(['Ventas Diarias']);
  });

  it('oculta el grupo cuando no queda ningun submenu visible', () => {
    expect(titles(filterByPermission(menu, () => false))).not.toContain('Reportes');
  });

  it('no modifica el menu original', () => {
    filterByPermission(menu, () => false);
    expect(menu[1].submenu.length).toBe(2);
  });
});
