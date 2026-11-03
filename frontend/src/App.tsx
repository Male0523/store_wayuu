import { lazy, Suspense, useEffect, useState, type ComponentType, type FormEvent, type ReactNode } from 'react'
import { useUserSession } from './context/user-context'
import type { SessionUser } from './types'

const legacyViews = import.meta.glob<ComponentType>('../../*.tsx', { import: 'default' })
const PublicSite = lazy(() => legacyViews['../../sitio_p_blico_tienda_artesanal_way_u.tsx']().then((module) => ({ default: module })))
const AdministratorPanel = lazy(() => legacyViews['../../way_u_store_administrator_panel.tsx']().then((module) => ({ default: module })))
const SuperadministratorPanel = lazy(() => legacyViews['../../panel_de_control_superadministrador_way_u.tsx']().then((module) => ({ default: module })))
const CustomerPanel = lazy(() => import('./CustomerPanel'))
const ConnectedShop = lazy(() => import('./ShopApp').then((module) => ({ default: module.ConnectedShop })))

type Role = SessionUser['role']

const roleRoutes: { path: string; label: string; role: Role }[] = [
	{ path: '/cliente', label: 'Cliente', role: 'customer' },
	{ path: '/tejedora', label: 'Tejedora', role: 'craftswoman' },
	{ path: '/admin', label: 'Administración', role: 'admin' },
	{ path: '/superadmin', label: 'Superadministración', role: 'superadmin' },
]

function DemoNotice() {
	return (
		<div className="demo-notice" role="note">
			Interfaz original · datos demostrativos temporales; los cambios no se guardan en Django.
		</div>
	)
}

function AccessGate({ user, onLogin }: {
	user: SessionUser | null
	onLogin: (event: FormEvent<HTMLFormElement>) => Promise<void>
}) {
	const [error, setError] = useState('')
	const [busy, setBusy] = useState(false)

	async function submit(event: FormEvent<HTMLFormElement>) {
		setBusy(true)
		setError('')
		try {
			await onLogin(event)
		} catch (reason) {
			setError(reason instanceof Error ? reason.message : 'No fue posible iniciar sesión.')
		} finally {
			setBusy(false)
		}
	}

	if (user) {
		const destination = roleRoutes.find((route) => route.role === user.role)
		return (
			<section className="access-panel" aria-live="polite">
				<h1>Esta vista no está disponible para tu cuenta</h1>
				<p>La sesión actual no tiene el rol requerido. Los permisos reales se validan en Django.</p>
				{destination && <a className="primary-link" href={destination.path}>{destination.label}</a>}
			</section>
		)
	}

	return (
		<section className="access-panel">
			<h1>Inicia sesión para continuar</h1>
			<p>El acceso se consulta en Django. Esta pantalla no asigna ni permite cambiar roles.</p>
			<form className="access-form" onSubmit={submit}>
				<label>Usuario<input name="username" autoComplete="username" required /></label>
				<label>Contraseña<input name="password" type="password" autoComplete="current-password" required /></label>
				{error && <p className="form-error" role="alert">{error}</p>}
				<button className="primary-link" type="submit" disabled={busy}>{busy ? 'Validando…' : 'Iniciar sesión'}</button>
			</form>
		</section>
	)
}

function RolePage({ user, role, onLogin, children, connected = false }: {
	user: SessionUser | null
	role: Role
	onLogin: (event: FormEvent<HTMLFormElement>) => Promise<void>
	children: ReactNode
	connected?: boolean
}) {
	if (user?.role !== role) return <AccessGate user={user} onLogin={onLogin} />
	if (role === 'craftswoman' && user.profile?.active === false) {
		return <section className="access-panel"><h1>Cuenta pendiente de activación</h1><p>La administración debe activar el perfil antes de habilitar el panel de tejedora.</p></section>
	}
	return connected ? <>{children}</> : <><DemoNotice />{children}</>
}

export default function App() {
	const [path, setPath] = useState(window.location.pathname)
	const [logoutError, setLogoutError] = useState('')
	const { user, loaded: sessionLoaded, sessionError, login: loginUser, logout: logoutUser } = useUserSession()

	useEffect(() => {
		const syncPath = () => setPath(window.location.pathname)
		window.addEventListener('popstate', syncPath)
		return () => {
			window.removeEventListener('popstate', syncPath)
		}
	}, [])

	function navigate(event: React.MouseEvent<HTMLAnchorElement>, destination: string) {
		if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
		event.preventDefault()
		window.history.pushState(null, '', destination)
		setPath(destination)
	}

	async function login(event: FormEvent<HTMLFormElement>) {
		event.preventDefault()
		const values = new FormData(event.currentTarget)
		const account = await loginUser(String(values.get('username')), String(values.get('password')))
		const destination = roleRoutes.find((route) => route.role === account.role)?.path ?? '/tienda'
		window.history.pushState(null, '', destination)
		setPath(destination)
	}

	async function logout() {
		setLogoutError('')
		try {
			await logoutUser()
		} catch {
			setLogoutError('No se pudo cerrar la sesión con Django. Revisa la conexión e inténtalo de nuevo.')
			return
		}
		window.history.pushState(null, '', '/')
		setPath('/')
	}

	function protectedPage(role: Role, page: ReactNode, connected = false) {
		if (!sessionLoaded) return <div className="route-loading" role="status">Comprobando sesión…</div>
		return <RolePage user={user} role={role} onLogin={login} connected={connected}>{page}</RolePage>
	}

	let page: ReactNode
	switch (path.replace(/\/$/, '') || '/') {
		case '/': page = <><DemoNotice /><PublicSite /></>; break
		case '/cliente': page = protectedPage('customer', <CustomerPanel />, true); break
		case '/tienda': page = <ConnectedShop key="tienda" initialScreen="shop" />; break
		case '/tejedora': page = protectedPage('craftswoman', <ConnectedShop key="tejedora" initialScreen="craftswoman" />, true); break
		case '/admin': page = protectedPage('admin', <AdministratorPanel />); break
		case '/superadmin': page = protectedPage('superadmin', <SuperadministratorPanel />); break
		default: page = <section className="access-panel"><h1>Página no encontrada</h1><a className="primary-link" href="/" onClick={(event) => navigate(event, '/')}>Volver al inicio</a></section>
	}

	return (
		<>
			<header className="unified-header">
				<a className="unified-brand" href="/" onClick={(event) => navigate(event, '/')}>STORE WAYUU</a>
				<nav aria-label="Navegación de la aplicación">
					<a href="/" onClick={(event) => navigate(event, '/')}>Sitio público</a>
					<a href="/tienda" onClick={(event) => navigate(event, '/tienda')}>Tienda conectada</a>
					{roleRoutes.filter((route) => route.role === user?.role).map((route) => (
						<a key={route.path} href={route.path} onClick={(event) => navigate(event, route.path)}>{route.label}</a>
					))}
				</nav>
				{user && <button className="session-button" type="button" onClick={logout}>Cerrar sesión</button>}
			</header>
			{logoutError && <p className="form-error" role="alert">{logoutError}</p>}
			{sessionError && <p className="form-error" role="status">{sessionError}</p>}
			<main>
				<Suspense fallback={<div className="route-loading" role="status">Cargando interfaz…</div>}>
					{page}
				</Suspense>
			</main>
			<footer className="authorization-note">
				La protección de rutas en el navegador es solo de navegación. Django debe autorizar cada operación y endpoint.
			</footer>
		</>
	)
}
